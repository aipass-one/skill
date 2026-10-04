# WebMCP for AI Pass browser apps

Use this path only for a browser surface when the user requests WebMCP, an agent-ready website, or a concrete browser-agent journey. WebMCP registers tools in the active page through `document.modelContext`; it is not the authenticated AI Pass remote MCP server at `POST /mcp`, and it does not replace OAuth, the AI Pass SDK, or server authorization.

WebMCP is an experimental progressive enhancement. The app must remain fully usable through its ordinary human interface when `document.modelContext` is absent.

For local verification, use a Chromium build that implements WebMCP and enable its documented WebMCP testing flag. While Chrome requires an origin trial for production use, the owner of each exact app origin must enroll that origin and serve its token according to the current Chrome instructions; a token for `aipass.one` cannot enable a third-party app origin. Do not block the integration on enrollment, invent a token, or treat browser enrollment as AI Pass authorization.

## Choose the smallest tool surface

- Expose one clear product action per tool. Do not publish the whole AI Pass SDK or make overlapping aliases.
- Prefer the declarative API for an existing semantic form. Prefer the imperative API for JavaScript actions, navigation, or state that has no natural form.
- Register a tool only while it is valid in the current page state, and unregister it on component teardown or when the action becomes unavailable.
- Accept raw user intent with specific JSON types. Validate again inside `execute`; the schema is guidance, not an authorization boundary.
- Keep descriptions under 500 characters, parameter descriptions under 150 characters, and successful outputs compact. Return JSON-serializable values and update the visible interface before resolving.
- Mark a tool `readOnlyHint: true` only when it neither changes state nor spends wallet funds. Mark outputs containing user-generated or external text with `untrustedContentHint: true`.

## Imperative SDK bridge

The AI Pass SDK exposes `AiPass.webMcp` even in browsers without WebMCP. Unsupported browsers receive an inert registration handle, so do not load a polyfill or weaken browser security settings.

```javascript
const registration = await AiPass.webMcp.registerTool({
  name: 'draft_product_caption',
  title: 'Draft product caption',
  description: 'Draft a caption and place it in the visible editor.',
  inputSchema: {
    type: 'object',
    properties: {
      product: { type: 'string', description: 'Product facts to use in the caption.' },
      tone: { type: 'string', enum: ['plain', 'playful', 'premium'] }
    },
    required: ['product', 'tone']
  },
  annotations: {
    readOnlyHint: false,
    untrustedContentHint: false
  },
  execute: async ({ product, tone }, { signal }) => {
    if (typeof product !== 'string' || product.trim().length === 0) {
      throw new Error('Product facts are required.');
    }
    const result = await AiPass.generateCompletion({
      model: selectedTextModel,
      messages: [{
        role: 'user',
        content: `Draft a ${tone} caption from these facts: ${product}`
      }],
      signal
    });
    const caption = result.choices[0].message.content;
    document.querySelector('#caption').value = caption;
    document.querySelector('#status').textContent = 'Caption ready';
    return { caption };
  }
}, {
  confirmation: ({ product }) => ({
    title: 'Generate with AI Pass?',
    message: `Use the connected AI Pass wallet to draft a caption for ${product}?`,
    confirmLabel: 'Generate'
  })
});

if (!registration.supported) {
  // The normal button/form remains the complete fallback experience.
}

// Component teardown or state transition:
registration.unregister();
```

`registerTool()` forwards the WebMCP execution `AbortSignal`, uses an internal registration signal for cleanup, and confirms non-read-only tools by default. Supply a specific `confirmation` message for paid calls. Set `confirmation: false` only when the normal action handler presents an equivalent visible confirmation before any consequential mutation or wallet spend.

Use `registerTools([...])` for a set that must register atomically. Its handle unregisters the whole set. `unregister(name)` and `unregisterAll()` are available for framework cleanup.

Do not pass `exposedTo` unless the product explicitly requires a trusted cross-origin iframe workflow. When it is required, list only exact HTTPS origins approved for that data and action. Never expose tokens, credentials, private prompts, wallet details, `AiPass.data`, `AiPass.files`, or `AiPass.shared` merely for agent convenience.

## Declarative forms

Annotate an existing visible form without replacing its submit handler:

```javascript
const formTool = AiPass.webMcp.annotateForm('#catalog-search', {
  name: 'search_catalog',
  description: 'Fill and submit the visible product catalog search form.',
  parameters: {
    query: 'Words describing the products to find.'
  }
});

// Restore the form's previous attributes on teardown.
formTool.unregister();
```

The native equivalent is:

```html
<form toolname="search_catalog"
      tooldescription="Fill and submit the visible product catalog search form.">
  <label>
    Search
    <input name="query" toolparamdescription="Words describing the products to find.">
  </label>
  <button type="submit">Search</button>
</form>
```

Declarative WebMCP fills and activates the real form, so retain labels, constraints, validation, focus behavior, submit confirmation, and accessible error messages. A WebMCP attribute is not an authorization check.

## Verification

1. Prove the normal button or form still works in a browser without WebMCP.
2. Unit-test registration, schema forwarding, cancellation, confirmation decline, successful execution, visible UI state, and cleanup with a fake `document.modelContext`.
3. In an experimental WebMCP browser, inspect the registered tool, execute it manually, and verify that no paid request occurs before confirmation.
4. Include direct and ambiguous agent prompts in evals. Confirm the agent selects this tool only for its intended journey and treats untrusted outputs as data rather than instructions.
5. Do not make a real wallet-funded eval call without the user's separate approval under the main verification rules.
