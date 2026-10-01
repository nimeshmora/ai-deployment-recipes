"""Exercise the request-path safeguards and print what each one does.

Black-box: sends HTTP only, like smoke.py. Run after the app is up in mock mode.
Checks 1-8 are observed over HTTP. Check 9 (redacted logs) is verified separately
with `docker compose logs` because logs are not exposed over HTTP; this script
prints the exact command and a request ID to look for.

The rate-limit check consumes the per-minute budget. Run it on a fresh window
(for example, right after `docker compose up`), or wait 60 seconds between runs.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.getenv("APP_URL", "http://127.0.0.1:8000").rstrip("/")
TOKEN = (Path(__file__).resolve().parents[1] / ".secrets" / "app_token").read_text().strip()


def call(path, data=None, token=None, content_type="application/json"):
    """Return (status, response_headers). Sends raw bytes so oversized bodies are testable."""
    headers = {}
    if content_type is not None:
        headers["Content-Type"] = content_type
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
    request = urllib.request.Request(BASE + path, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return response.status, dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers)


results = []


def check(number, name, why, expected, got, ok):
    mark = "PASS" if ok else "FAIL"
    results.append(ok)
    print(f"[{mark}] {number}. {name}")
    print(f"        why it matters : {why}")
    print(f"        expected       : {expected}")
    print(f"        observed       : {got}\n")


# 1. Anonymous request is rejected.
status, _ = call("/api/chat", {"message": "hi"}, token=None)
check(1, "Authentication (no token)",
      "Blocks anonymous traffic from spending your model budget.",
      "401", status, status == 401)

# 2. Wrong token is rejected (constant-time comparison in the app).
status, _ = call("/api/chat", {"message": "hi"}, token="wrong-token-value-1234567890")
check(2, "Authentication (wrong token)",
      "A guessed or stale token still cannot call the model.",
      "401", status, status == 401)

# 3. Non-JSON content type is rejected even with a valid token.
status, _ = call("/api/chat", {"message": "hi"}, token=TOKEN, content_type="text/plain")
check(3, "Content-type enforcement",
      "Only declared application/json is processed.",
      "415", status, status == 415)

# 4. Message longer than 4000 characters is rejected by the schema.
status, _ = call("/api/chat", {"message": "a" * 5000}, token=TOKEN)
check(4, "Input length limit",
      "An over-long prompt is refused before it reaches the model.",
      "422", status, status == 422)

# 5. Body larger than 16 KiB is rejected before JSON parsing.
oversized = b'{"message":"' + b"a" * 20000 + b'"}'
status, _ = call("/api/chat", oversized, token=TOKEN)
check(5, "Raw body size limit",
      "A huge payload is dropped before parsing, protecting memory.",
      "413", status, status == 413)

# 6. Unknown fields are rejected (strict schema).
status, _ = call("/api/chat", {"message": "hi", "admin": True}, token=TOKEN)
check(6, "Strict request schema",
      "Smuggled extra fields (e.g. admin flags) are refused.",
      "422", status, status == 422)

# 7. Rate limit: burst past REQUESTS_PER_MINUTE and watch throttling begin.
accepted = throttled = other = 0
for _ in range(40):
    status, _ = call("/api/chat", {"message": "hi"}, token=TOKEN)
    if status == 200:
        accepted += 1
    elif status == 429:
        throttled += 1
    else:
        other += 1
check(7, "Rate limiting",
      "One caller cannot flood the service; excess is throttled with 429.",
      "some 200 then 429 (default budget is 30/min)",
      f"accepted(200)={accepted}, throttled(429)={throttled}, other={other}",
      throttled >= 1)

# 8. Security headers and a correlation request ID are present.
status, resp_headers = call("/api/chat", {"message": "hi"}, token=TOKEN)
lower = {k.lower(): v for k, v in resp_headers.items()}
required = ["x-request-id", "content-security-policy", "x-content-type-options",
            "referrer-policy", "cache-control"]
present = [h for h in required if h in lower]
check(8, "Security headers + request ID",
      "Hardened browser headers; request ID lets you trace one call in logs.",
      f"all present: {required}",
      f"present: {present}",
      len(present) == len(required))
request_id = lower.get("x-request-id", "<none>")

# 9. Redacted logs: verified against docker logs, not over HTTP.
print("[INFO] 9. Redacted logs (verify yourself)")
print("        why it matters : Prompts, answers, and tokens never land in logs.")
print("        how to verify  : run the two commands below.\n")
print("   docker compose logs --no-log-prefix app | grep http_request | tail -5")
print(f"   # Every line is just status + duration + request_id (e.g. {request_id}).")
print("   # Now confirm your message and token are absent:")
print("   docker compose logs --no-log-prefix app | grep -c hi        # expect 0")
print("   docker compose logs --no-log-prefix app | grep -c Bearer    # expect 0\n")

passed = sum(results)
total = len(results)
print(f"Summary: {passed}/{total} HTTP-observable safeguards behaved as expected "
      "(check 9 is verified with the log commands above).")
raise SystemExit(0 if passed == total else 1)
