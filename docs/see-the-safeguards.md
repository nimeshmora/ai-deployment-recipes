# See the safeguards yourself

The chat response is deliberately trivial. The real content of this recipe is the
set of controls every request must pass before it reaches a model. This page lets
you watch each one act, so the value is observable rather than asserted.

Two ways to do it:

- **Fast:** run one script that exercises checks 1–8 and prints a result for each.
- **By hand:** send each request yourself with `curl` and read the status code.

Either way, the behaviors here are also locked in by the automated test suite (see
[verification record](verification.md)); this page is for seeing them live.

## Before you start

Start the app in mock mode and keep it running (from `recipes/01-ai-app`):

```bash
python3 scripts/init_local.py
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
docker compose up --build -d --wait
```

Set a couple of shell values the examples below reuse (POSIX shells):

```bash
export APP_URL=http://localhost:8000
export TOKEN=$(cat .secrets/app_token)
```

## Option A — run the script

```bash
python3 scripts/show_safeguards.py
```

It prints `PASS`/`FAIL` for checks 1–8 with a one-line reason for each, then prints
the two commands for check 9 (log redaction). Expected ending:

```
Summary: 8/8 HTTP-observable safeguards behaved as expected ...
```

Note: check 7 (rate limiting) spends the per-minute budget. Run the script on a
fresh window — right after `docker compose up` — or wait 60 seconds between runs,
or you will see fewer than 30 accepted requests.

## Option B — see each one by hand

Each command prints only the HTTP status code so the result is unambiguous.

### 1. Authentication — no token → `401`

A request with no credentials never reaches the model. This is what stops anonymous
internet traffic from running up your bill.

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST $APP_URL/api/chat \
  -H 'Content-Type: application/json' -d '{"message":"hi"}'
# 401
```

### 2. Authentication — wrong token → `401`

A guessed or stale token is rejected too (the app compares tokens in constant time).

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST $APP_URL/api/chat \
  -H 'Authorization: Bearer not-the-real-token' \
  -H 'Content-Type: application/json' -d '{"message":"hi"}'
# 401
```

### 3. Content-type enforcement — not JSON → `415`

Even with a valid token, only `application/json` is processed.

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST $APP_URL/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: text/plain' -d '{"message":"hi"}'
# 415
```

### 4. Input length limit — message over 4000 chars → `422`

An over-long prompt is refused by the schema before any model call.

```bash
BIG=$(printf 'a%.0s' $(seq 1 5000))
curl -s -o /dev/null -w "%{http_code}\n" -X POST $APP_URL/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d "{\"message\":\"$BIG\"}"
# 422
```

### 5. Raw body size limit — body over 16 KiB → `413`

A very large payload is dropped before JSON is even parsed, protecting memory.

```bash
HUGE=$(printf 'a%.0s' $(seq 1 20000))
curl -s -o /dev/null -w "%{http_code}\n" -X POST $APP_URL/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d "{\"message\":\"$HUGE\"}"
# 413
```

### 6. Strict request schema — unknown field → `422`

Extra fields (for example a smuggled `admin` flag) are rejected, not ignored.

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST $APP_URL/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"message":"hi","admin":true}'
# 422
```

### 7. Rate limiting — burst of requests → `429` once the budget is spent

The default budget is 30 admitted requests per 60-second window. Send 40 quickly and
count how many are throttled. Run this on a fresh window (right after startup).

```bash
accepted=0; throttled=0
for i in $(seq 1 40); do
  s=$(curl -s -o /dev/null -w "%{http_code}" -X POST $APP_URL/api/chat \
      -H "Authorization: Bearer $TOKEN" \
      -H 'Content-Type: application/json' -d '{"message":"hi"}')
  [ "$s" = 200 ] && accepted=$((accepted+1))
  [ "$s" = 429 ] && throttled=$((throttled+1))
done
echo "accepted=$accepted throttled=$throttled"
# accepted=30 throttled=10
```

Only successful (admitted) requests spend the budget; the 401/415/422/413 responses
above do not. After 60 seconds the window resets.

### 8. Security headers + request ID

Every response carries hardened browser headers and a unique request ID you can trace
in the logs. Print the response headers:

```bash
curl -s -D - -o /dev/null -X POST $APP_URL/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"message":"hi"}' \
  | grep -iE 'x-request-id|content-security-policy|x-content-type-options|referrer-policy|cache-control'
```

You should see `x-request-id`, `content-security-policy`, `x-content-type-options:
nosniff`, `referrer-policy: no-referrer`, and `cache-control: no-store`.

### 9. Redacted logs — your prompt and token never appear

The app logs only a status, a duration, and the request ID — never the message, the
answer, or the token. After running some of the requests above:

```bash
docker compose logs --no-log-prefix app | grep http_request | tail -5
# Each line looks like: {"event": "http_request", "request_id": "...", "status": 200, "duration_ms": 1.2}

docker compose logs --no-log-prefix app | grep -c hi        # expect 0
docker compose logs --no-log-prefix app | grep -c Bearer    # expect 0
```

The counts are `0`: the words you sent and the token you used are absent from the logs.

## What this demonstrates

| # | Safeguard | You see | Why it matters |
|---|---|---|---|
| 1 | Authentication (no token) | `401` | Anonymous callers can't spend your model budget |
| 2 | Authentication (wrong token) | `401` | A stale/guessed token still can't call the model |
| 3 | Content-type enforcement | `415` | Only declared JSON is processed |
| 4 | Input length limit | `422` | Over-long prompts refused before the model |
| 5 | Raw body size limit | `413` | Huge payloads dropped before parsing |
| 6 | Strict request schema | `422` | Smuggled extra fields rejected |
| 7 | Rate limiting | `30` ok, rest `429` | One caller can't flood the service |
| 8 | Security headers + request ID | headers present | Hardened responses; traceable requests |
| 9 | Redacted logs | grep counts `0` | Prompts, answers, tokens never logged |

A request has to survive all of these to get an answer. Reproducing them is the point
of the recipe: the safeguards are things you can run, not claims you have to trust.

For how each one maps to the OWASP LLM Top 10 and OWASP API Security Top 10 — and what
this recipe deliberately does not cover — see [the OWASP mapping](owasp-mapping.md).

When you are done: `docker compose down`.
