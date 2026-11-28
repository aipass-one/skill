#!/usr/bin/env python3
"""Ask for one AI Pass approval and deliver the key to Firebase Secret Manager."""
import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ORIGIN = "https://aipass.one"
SECRET_MANAGER = "https://secretmanager.googleapis.com/v1"
SCOPE = "app-funding:provision"
DEVICE = "/api/v1/agent-auth/device"
TOKEN = "/api/v1/agent-auth/token"
ISSUE = "/api/v1/agent-control/app-funding/key"
CONFIRM = "/api/v1/agent-control/app-funding/confirm-delivery"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ApiError(Exception):
    def __init__(self, status, code):
        self.status = status
        self.code = code


def request_json(url, body, bearer=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    request = urllib.request.Request(url, json.dumps(body).encode(), headers=headers, method="POST")
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=20) as response:
            return None if response.status == 204 else json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            code = json.load(exc).get("error")
        except (ValueError, AttributeError):
            code = None
        raise ApiError(exc.code, code) from None


def post(path, body=None, bearer=None):
    response = request_json(ORIGIN + path, body or {}, bearer)
    return response["data"] if response is not None else None

def wait_for_approval(device):
    deadline = time.monotonic() + min(device["expiresIn"], 600)
    interval = max(5, device["interval"])
    while time.monotonic() + interval < deadline:
        time.sleep(interval)
        try:
            grant = post(TOKEN, {"deviceCode": device["deviceCode"]})
        except ApiError as exc:
            if exc.code == "authorization_pending":
                continue
            if exc.code == "slow_down" or exc.status == 429:
                interval += 5
                continue
            if exc.code in ("access_denied", "expired_token"):
                raise RuntimeError("Approval was declined or expired.") from None
            raise
        if grant["scopes"] != [SCOPE]:
            raise RuntimeError("AI Pass returned an unexpected approval scope.")
        return grant["accessToken"]
    raise RuntimeError("The AI Pass approval window expired.")


def google_access_token(gcloud, account):
    command = [gcloud, "auth", "print-access-token", "--quiet", "--no-log-http"]
    if account:
        command.extend(["--account", account])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("Google Cloud login could not be verified.") from None
    token = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
        raise RuntimeError("Google Cloud login is required for the approved Secret Manager project.")
    return token


def save_to_secret_manager(target, funding_key, google_token):
    project_url = f"{SECRET_MANAGER}/projects/{target['projectId']}/secrets"
    name = target["secretName"]
    version_url = f"{project_url}/{name}:addVersion"
    payload = {"payload": {"data": base64.b64encode(funding_key.encode()).decode()}}
    try:
        request_json(version_url, payload, google_token)
    except ApiError as exc:
        if exc.status != 404:
            raise
    else:
        return

    try:
        request_json(f"{project_url}?secretId={name}", {"replication": {"automatic": {}}}, google_token)
    except ApiError as exc:
        if exc.status != 409:  # A concurrent explicitly approved setup created the same secret.
            raise
    request_json(version_url, payload, google_token)

def confirm(bearer):
    for attempt in range(3):
        try:
            post(CONFIRM, bearer=bearer)
            return True
        except ApiError as exc:
            if exc.status != 429 and not 500 <= exc.status < 600:
                return False
        except OSError:
            pass
        if attempt < 2:
            time.sleep(2)
    return False


def provision(gcloud, target, google_account):
    google_token = google_access_token(gcloud, google_account)
    fingerprint = hashlib.sha256(json.dumps(target, sort_keys=True).encode()).hexdigest()
    device = post(DEVICE, {"agentName": "AI Pass funding setup", "projectFingerprint": fingerprint,
                           "requestedScopes": [SCOPE], "fundingKeyTarget": target})
    user_code = device["userCode"]
    if not re.fullmatch(r"[A-Z0-9]{4}-[A-Z0-9]{4}", user_code):
        raise RuntimeError("AI Pass returned an invalid approval code.")
    print(f"Approve the funding setup at {ORIGIN}/agent/authorize?user_code={user_code}", flush=True)
    bearer = wait_for_approval(device)
    result = post(ISSUE, bearer=bearer)
    issued = result["credential"]
    key_id = int(issued["key"]["id"])
    returned = result["target"]
    if (any(returned.get(k) != value for k, value in target.items())
            or not re.fullmatch(r"afk_[A-Za-z0-9_-]{43}", issued["token"])):
        raise RuntimeError(f"Unexpected response for issued key #{key_id}. Review it in App funding.")
    try:
        save_to_secret_manager(target, issued["token"], google_token)
    except ApiError as exc:
        raise RuntimeError(f"Secret Manager returned HTTP {exc.status} for key #{key_id}. "
                           "Check write permissions and the destination’s versions before retrying.") from None
    except (OSError, ValueError):
        raise RuntimeError(f"Secret Manager delivery for key #{key_id} could not be confirmed. "
                           "Check the destination’s versions and App funding before retrying.") from None
    if not confirm(bearer):
        raise RuntimeError(f"Key #{key_id} was stored in Secret Manager. "
                           "AI Pass did not confirm delivery. Check App funding before retiring an existing key.")
    print(f"Stored app funding key #{key_id} in {target['projectId']}/{target['secretName']}.")
    if target["retireKeyId"] is not None:
        print(f"Retired funding key #{target['retireKeyId']}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--project", required=True, help="Firebase project ID")
    parser.add_argument("--secret", required=True, help="Backend secret name")
    parser.add_argument("--account", help="Authorized Google Cloud CLI login")
    parser.add_argument("--retire-key-id", type=int, help="Revoke this app's key after the new version is stored")
    args = parser.parse_args()
    if (not re.fullmatch(r"[A-Za-z0-9._~-]{1,255}", args.client_id)
            or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", args.project)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", args.secret)
            or args.retire_key_id is not None and args.retire_key_id <= 0):
        parser.error("Provide a valid OAuth client ID, Firebase project ID, secret name, and optional positive key ID.")
    gcloud = shutil.which("gcloud")
    if gcloud is None:
        parser.error("An authorized Google Cloud CLI is required.")
    target = {"clientId": args.client_id, "projectId": args.project, "secretName": args.secret,
              "retireKeyId": args.retire_key_id}
    try:
        provision(gcloud, target, args.account)
    except ApiError as exc:
        print(f"AI Pass setup request failed (HTTP {exc.status}). Check the approval and App funding panel.", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError):
        print("Funding setup could not be confirmed. Check App funding before requesting another key.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
