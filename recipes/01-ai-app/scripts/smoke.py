"""Black-box smoke check. Live mode makes one potentially billable model call."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

base = os.getenv("APP_URL", "http://127.0.0.1:8000").rstrip("/")
token = (Path(__file__).resolve().parents[1] / ".secrets" / "app_token").read_text().strip()


def call(path, data=None, auth=False):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


assert call("/health/live")[0] == 200
status, health = call("/health/ready")
assert status == 200
assert call("/api/chat", {"message": "Hello"})[0] == 401
status, body = call("/api/chat", {"message": "Reply with a short greeting."}, auth=True)
assert status == 200, (status, body)
assert body["mode"] == health["mode"]
assert isinstance(body["answer"], str) and body["answer"]
print(f"PASS: liveness, readiness, authentication, {body['mode']} completion")
