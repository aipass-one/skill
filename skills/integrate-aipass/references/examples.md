# Secure Integration Examples

These examples are framework-neutral starting points. Adapt database and HTTP primitives to the host application. They intentionally contain placeholders, not credentials.

## PKCE and Authorization URL

```ts
import { createHash, randomBytes } from 'node:crypto';

const base64url = (value: Buffer) => value.toString('base64url');

export function createPkce() {
  const verifier = base64url(randomBytes(32));
  const challenge = createHash('sha256')
    .update(verifier, 'ascii')
    .digest('base64url');
  return { verifier, challenge };
}

export function buildAuthorizeUrl(input: {
  clientId: string;
  redirectUri: string;
  state: string;
  challenge: string;
}) {
  const url = new URL('https://aipass.one/oauth2/authorize');
  url.search = new URLSearchParams({
    response_type: 'code',
    client_id: input.clientId,
    redirect_uri: input.redirectUri,
    scope: 'api:access profile:read',
    state: input.state,
    code_challenge: input.challenge,
    code_challenge_method: 'S256',
  }).toString();
  return url.toString();
}
```

Store a hash of `state`, not the raw state, and encrypt the verifier. Never accept the redirect URI directly from an untrusted request when the host application has a known callback.

## Code Exchange

```ts
type TokenResponse = {
  access_token: string;
  token_type: 'Bearer' | string;
  expires_in: number;
  refresh_token: string;
  scope?: string;
};

export async function exchangeCode(input: {
  baseUrl: string;
  clientId: string;
  code: string;
  verifier: string;
  redirectUri: string;
  signal?: AbortSignal;
}): Promise<TokenResponse> {
  const response = await fetch(`${input.baseUrl}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      grantType: 'authorization_code',
      clientId: input.clientId,
      code: input.code,
      codeVerifier: input.verifier,
      redirectUri: input.redirectUri,
    }),
    signal: input.signal,
  });

  if (!response.ok) throw new Error(`AIPASS_CODE_EXCHANGE_${response.status}`);
  const token = await response.json() as Partial<TokenResponse>;
  if (
    !token.access_token ||
    !token.refresh_token ||
    !Number.isFinite(token.expires_in) ||
    Number(token.expires_in) <= 0
  ) {
    throw new Error('AIPASS_INVALID_TOKEN_RESPONSE');
  }
  return token as TokenResponse;
}
```

Do not attach response text to client-facing errors; it may contain sensitive context.

## Atomic State Consumption

Use one database operation whose predicate includes unconsumed and unexpired state:

```sql
update aipass_oauth_states
set consumed_at = now()
where state_hash = :state_hash
  and consumed_at is null
  and created_at >= now() - interval '10 minutes'
returning code_verifier_ciphertext, redirect_uri, mode, bound_user_id;
```

Exactly one callback may receive a row. Zero returned rows means invalid, replayed, or expired state.

## Token Manager Skeleton

```ts
type StoredTokens = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  scope?: string;
  version: number;
};

const refreshes = new Map<string, Promise<string>>();

export async function getFreshAccessToken(userId: string): Promise<string> {
  const current = await loadAndDecryptTokens(userId);
  if (current.expiresAt > Date.now() + 60_000) return current.accessToken;

  const running = refreshes.get(userId);
  if (running) return running;

  const next = refreshAndPersist(userId, current).finally(() => {
    refreshes.delete(userId);
  });
  refreshes.set(userId, next);
  return next;
}

async function refreshAndPersist(userId: string, current: StoredTokens) {
  const response = await refreshWithOneConflictRetry(current.refreshToken);
  const receivedAt = Date.now();
  const next = {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    expiresAt: receivedAt + response.expires_in * 1000,
    scope: response.scope,
  };

  // encryptAndCompareAndSwap must update only if version is still current.
  const saved = await encryptAndCompareAndSwap(userId, current.version, next);
  if (!saved) {
    // Another worker may have won. Reload its durable pair; never overwrite it.
    const winner = await loadAndDecryptTokens(userId);
    if (winner.expiresAt <= Date.now()) throw new Error('AIPASS_TOKEN_PERSIST_FAILED');
    return winner.accessToken;
  }
  return next.accessToken;
}
```

The undefined persistence helpers represent the host application's encrypted repository. They must never store plaintext.

## Refresh Request with One 503 Retry

```ts
async function refreshWithOneConflictRetry(refreshToken: string) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const response = await fetch('https://aipass.one/oauth2/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        grantType: 'refresh_token',
        refreshToken,
        clientId: process.env.AIPASS_CLIENT_ID,
      }),
    });

    if (response.ok) return response.json();
    if (response.status === 503 && attempt === 0) {
      const seconds = Number(response.headers.get('Retry-After') ?? 0.25);
      await new Promise(resolve => setTimeout(resolve, Math.min(seconds, 1) * 1000));
      continue;
    }
    if (response.status === 400 || response.status === 401) {
      throw new Error('AIPASS_REAUTH_REQUIRED');
    }
    throw new Error(`AIPASS_TOKEN_REFRESH_${response.status}`);
  }
  throw new Error('AIPASS_TOKEN_REFRESH_FAILED');
}
```

In production, parse the OAuth error code too and mark reauthorization specifically for `invalid_grant`.

## Authenticated Request with One Refresh Retry

```ts
export async function aipassJson(
  userId: string,
  path: string,
  init: RequestInit,
) {
  let token = await getFreshAccessToken(userId);

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const response = await fetch(`https://aipass.one${path}`, {
      ...init,
      headers: {
        ...init.headers,
        Authorization: `Bearer ${token}`,
        'X-AIPass-OAuth-Client-Id': process.env.AIPASS_CLIENT_ID!,
      },
    });
    if (response.status !== 401 || attempt === 1) return response;
    token = await forceRefreshAccessToken(userId);
  }
  throw new Error('AIPASS_UNREACHABLE_RETRY_STATE');
}
```

Keep forced refresh serialized through the same manager.

## Model Discovery

The default `/v1/models` response is an OpenAI-compatible catalog envelope. Parse `data[].id` as the stable public IDs:

```ts
type ModelCatalog = {
  object: 'list';
  data: Array<{
    id: string;
    type?: string;
    capabilities?: string[];
    methods?: string[];
  }>;
};

export function normalizeModelIds(payload: unknown): string[] {
  if (Array.isArray(payload)) {
    return payload.filter((value): value is string => typeof value === 'string');
  }
  if (payload && typeof payload === 'object' && Array.isArray((payload as any).data)) {
    return (payload as ModelCatalog).data
      .map(model => model.id)
      .filter((id): id is string => typeof id === 'string');
  }
  throw new Error('AIPASS_INVALID_MODEL_CATALOG');
}
```

Use `type`, `capability`, and `method` query parameters to filter server-side. A string array is returned only when the request explicitly uses `?detailed=false`; accepting both shapes is useful for rolling upgrades and generic provider adapters. Cache discovery briefly, provide a configured stable-ID preference order, and handle the chosen model disappearing.

## Chat Provider Adapter

```ts
export async function generateWithAiPass(input: {
  userId: string;
  model: string;
  messages: Array<{ role: string; content: unknown }>;
  signal?: AbortSignal;
}) {
  const response = await aipassJson(input.userId, '/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: input.model,
      messages: input.messages,
      stream: false,
    }),
    signal: input.signal,
  });

  if (!response.ok) throw await classifyAiPassError(response);
  const result = await response.json();
  queueBalanceRefresh(input.userId); // non-blocking UI invalidation
  return result;
}
```

`classifyAiPassError` must distinguish auth, definite insufficient balance, model unavailable, invalid request, temporary provider failure, and ambiguous transport failure. Do not use broad string matching such as every `400` being “no balance.”

## Funding Router

```ts
export async function generate(input: GenerationInput) {
  const funding = await loadFundingState(input.userId);

  if (funding.source === 'app') {
    if (!funding.appCreditsAvailable) throw new Error('APP_CREDITS_EMPTY');
    const result = await generateWithExistingProvider(input);
    await debitOneAppCreditAfterSuccess(input.userId);
    return result;
  }

  try {
    return await generateWithAiPass(input);
  } catch (error) {
    if (!isDefiniteAiPassInsufficientBalance(error)) throw error;
    if (!funding.appCreditsAvailable) throw new Error('ALL_FUNDING_EMPTY');

    await persistFundingSource(input.userId, 'app');
    const result = await generateWithExistingProvider(input);
    await debitOneAppCreditAfterSuccess(input.userId);
    return result;
  }
}
```

Do not enter the catch branch for timeout, network, auth, provider, validation, or model errors. Do not call this router again from a nested fallback.

## Balance and Checkout

```ts
export async function getBalance(userId: string) {
  const response = await aipassJson(userId, '/api/v1/usage/me/summary', {
    method: 'GET',
  });
  if (!response.ok) throw await classifyAiPassError(response);
  const body = await response.json();
  return Number(body?.data?.remainingBudget ?? 0);
}

export async function createCheckout(userId: string, amount: number) {
  const response = await aipassJson(
    userId,
    '/api/v1/payment/create-checkout-session',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount }),
    },
  );
  if (!response.ok) throw await classifyAiPassError(response);
  const body = await response.json();
  const url = new URL(body?.data?.checkoutUrl);
  if (url.protocol !== 'https:') throw new Error('AIPASS_INVALID_CHECKOUT_URL');
  return url.toString();
}
```

For a configured local AI Pass instance, allow HTTP only for explicit loopback or trusted development hosts. The frontend should open a blank tab synchronously on click, request checkout, navigate that tab, and close it on failure.

## Disconnect

```ts
async function revoke(token: string, clientId: string) {
  await fetch('https://aipass.one/oauth2/revoke', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ token, client_id: clientId }),
  });
}

export async function disconnectAiPass(userId: string) {
  const tokens = await loadAndDecryptTokens(userId);
  await revoke(tokens.refreshToken, process.env.AIPASS_CLIENT_ID!).catch(() => {});
  await revoke(tokens.accessToken, process.env.AIPASS_CLIENT_ID!).catch(() => {});
  await deleteLocalAiPassIdentity(userId);
}
```

Remote failure must not leave local credentials active.
