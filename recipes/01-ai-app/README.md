# 01 · Deploy a small AI application

**What you'll build, in plain words:** a small web service (a chatbot-style API with a simple page) that runs in Docker and is set up the careful way — a token to get in, limits so it can't be abused, timeouts, redacted logs, and a locked-down container. By default it runs in **mock mode**: it replies with a fixed message and calls **no AI model**, so you can run it with **no API key and no cost** and focus on the deployment itself. Switch to *live mode* to point it at a real model endpoint.

This is **recipe 01, the reference example** — it covers the sections every recipe here uses (see the [recipe template](../TEMPLATE/README.md)), with extra depth. New here? Start with [§1 Run locally](#1-run-locally-with-docker-compose).

**Scope:** a stateless, single-turn text assistant on one application process. No conversation history, tool execution, database, RAG, streaming, or GPU is included in this recipe.

**Two modes:** `mock` returns a fixed labeled response without external calls; `live` calls an operator-configured Chat Completions endpoint. Live-mode wire behavior is tested against controlled fixtures; a real provider has not been tested in this release environment.

## 1. Run locally with Docker Compose

Requirements: Docker with Compose v2 supporting `up --wait`, plus Python 3.12+ for the included scripts. Run commands from this directory.

```bash
python3 scripts/init_local.py
cp .env.example .env
docker compose up --build -d --wait
python3 scripts/smoke.py
```

Open http://localhost:8000 and paste the contents of `.secrets/app_token` into the application-token field. Use the application token, never a model provider key. The UI retains the token in its input field only; it does not use local/session storage, cookies, or URL parameters. Reloading clears the application-managed state; browser/password-manager behavior is outside the application.

The port binds to `127.0.0.1`, not every host interface. Other services or users on your machine may still access it. Authentication is required for `/api/chat`; the static interface and health endpoints are public to anyone who can reach the port.

```bash
docker compose logs --tail=100 app
docker compose down
```

`down` removes this Compose deployment, not its local secret files.

### Secret files

The initialization script creates an owner-only `.secrets` directory on POSIX systems, with readable files inside so the container's UID 10001 can read Compose bind-mounted secrets. Existing values are preserved. Files are excluded from Git and the Docker build context. On Windows, review directory/file ACLs; POSIX mode bits do not provide equivalent protection.

Compose secrets here are local file mounts, not an encrypted secret vault. Anyone with host administrator or Docker-daemon access can read them. Use a managed secret facility for a deployed service. Do not copy these generated files into a public repository or container image.

## 2. Enable a live model endpoint

Edit `.env`:

```dotenv
MODEL_MODE=live
MODEL_BASE_URL=https://YOUR-ENDPOINT.example/v1
MODEL_NAME=YOUR-DEPLOYED-MODEL-ID
```

Replace both placeholders. `MODEL_BASE_URL` is the trusted API base including any version path; the adapter appends `/chat/completions`. It accepts HTTPS by default and rejects URL credentials, query parameters, and fragments. `ALLOW_HTTP_UPSTREAM=true` is an explicit opt-in for a trusted local/private HTTP endpoint; it does not make HTTP encrypted.

```bash
python3 scripts/set_model_key.py
docker compose up -d --force-recreate --wait
python3 scripts/smoke.py
```

The script prompts without echoing the key. A key may be empty for a trusted keyless endpoint. **The live smoke check makes one potentially billable model request.** Prompts are sent to your configured provider; review its data policies and retention settings.

### Exact supported API contract

The adapter sends a non-streaming POST with `model`, one `user` message, `max_tokens`, and `stream: false`. It expects JSON containing `choices[0].message.content` as non-empty text and an optional string `finish_reason`. The finish reason is returned to the client; the UI flags `length` as truncation.

Not all providers or models implement this exact subset. Some require `max_completion_tokens`, special headers, a different route, a chat template, or another API. Such integrations require an explicit adapter change and tests. This recipe does not claim universal provider compatibility. Provider errors, refusals without text, and tool-only responses are not silently converted into answers.

Docker's `localhost` is the container itself. An endpoint on the host needs platform-appropriate host addressing; a sibling Compose service normally uses its service DNS name. Do not change the URL to an untrusted endpoint: the configured API key and prompts will be sent there.

## 3. Understand the request path

1. Read at most 16 KiB of request body within five seconds, before JSON parsing.
2. Verify the shared bearer token using a constant-time comparison.
3. Require JSON containing only a non-blank `message` of at most 4,000 characters.
4. Apply the process-local rate window and immediate concurrency admission.
5. Return a labeled mock reply, or call the configured model service with explicit bounds.
6. Release the concurrency slot even when the task times out or is cancelled.
7. Return a request ID and log status/duration without recording content.

The body-size bound includes the entire encoded JSON body. A 4,000-character message can still exceed 16 KiB when JSON-escaped. Character limits are not token counts. Choose limits using your model's tokenizer and complete context budget when adapting this example.

To check these controls automatically, run the [readiness check](../../tools/readiness-check/README.md) against this app, or follow the [see the safeguards](../../docs/see-the-safeguards.md) walkthrough to trigger each one by hand.

## 4. Configuration

| Setting | Default | Meaning |
|---|---|---|
| `MODEL_MODE` | `mock` | `mock` or `live` |
| `APP_TOKEN_FILE` | Set by Compose | Path to application bearer token; >=32 ASCII characters |
| `MODEL_API_KEY_FILE` | Set by Compose | Path to model API key; may be empty |
| `MODEL_BASE_URL` | Empty | Required in live mode |
| `MODEL_NAME` | Empty | Required in live mode |
| `ALLOW_HTTP_UPSTREAM` | `false` | Explicitly permit unencrypted upstream HTTP |
| `MAX_INFLIGHT` | `4` | Maximum admitted model calls in this process; 1–32 |
| `REQUESTS_PER_MINUTE` | `30` | Admitted requests per process-local 60-second window; 1–10,000 |
| `UPSTREAM_DEADLINE_SECONDS` | `30` | Overall model-call deadline; >0 and <=30 seconds |
| `MAX_OUTPUT_TOKENS` | `256` | Forwarded as `max_tokens`; 1–4,096 |

Direct Python runs may use `APP_TOKEN` / `MODEL_API_KEY` instead of their `_FILE` settings. Defining both a non-empty value and its file setting fails startup. Compose uses files to avoid placing the values directly in its environment configuration.

The fixed window starts on the first relevant request and resets after 60 seconds. Requests rejected for authentication, validation, or concurrency do not consume the rate allowance. Admitted requests that fail upstream do consume it. Windows allow boundary bursts; counters reset on process restart. This is **not per-user billing control, a distributed limit, or denial-of-service protection**. Use one worker as configured.

## 5. Health, errors, and shutdown

| Endpoint / status | Meaning |
|---|---|
| `GET /health/live` | HTTP handler is responsive; no provider call |
| `GET /health/ready` | Local lifespan startup completed; reports mock/live mode |
| `401` | Missing/incorrect application token |
| `408` | Incoming body did not complete within five seconds |
| `413` | Body exceeds 16 KiB |
| `415` / `422` | Unsupported content type / invalid request |
| `429` | Local rate window exhausted; includes `Retry-After` |
| `503` | Local model-call capacity full, or upstream 429/5xx |
| `502` | Upstream rejected request, connection failed, oversized/invalid response, or unsupported encoding |
| `504` | Model-call phase timeout or overall deadline |

HTTPX uses a 5-second connect timeout, 1-second pool timeout, and 20-second read/write inactivity timeouts, inside the overall model-call deadline. Provider response bodies are limited to 256 KiB; compressed provider responses are rejected. Redirects are not followed and proxy environment variables are ignored by the client.

There are **no automatic retries**. A timed-out generation may still execute or be billed upstream. A browser disconnect does not guarantee immediate cancellation of the upstream call; the server-side deadline still applies. Retry only with an understood cost/side-effect policy.

Readiness does not prove the API key, model name, provider availability, or answer quality. A separate synthetic check or live smoke test is needed. Docker health checks only set container health status; `restart: unless-stopped` does not restart a process merely because it is unhealthy.

Uvicorn runs one worker, stops accepting new connections during shutdown, and allows up to 35 seconds for outstanding tasks. Compose allows 40 seconds before force termination. These are bounded shutdown settings, not a zero-downtime guarantee. The process has no persistent tasks to recover.

Application-generated request logs contain request ID, status, and elapsed time. Uvicorn access logging is disabled to avoid query-string logging. Infrastructure, proxies, and the model provider have their own logging behavior. Uvicorn can reject a connection at its own concurrency limit before application middleware; those responses may not carry application request IDs or headers.

## 6. Develop without Docker

POSIX shell, Python 3.12:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.txt
python scripts/init_local.py
export APP_TOKEN_FILE="$PWD/.secrets/app_token"
export MODEL_API_KEY_FILE="$PWD/.secrets/model_api_key"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log --no-proxy-headers --timeout-graceful-shutdown 35 --limit-concurrency 64
```

Direct Python runs do not automatically load `.env`; export live-mode settings explicitly. In a second terminal, run `python3 scripts/smoke.py` from this directory.

```bash
python -m pytest -q
ruff check .
ruff format --check .
```

For dependency updates, edit the `.in` files and regenerate both locks with `uv pip compile --generate-hashes --python-version 3.12`. Re-run tests, inspect advisories, and rebuild the container. The committed hashes verify package artifacts; they do not establish that dependencies are vulnerability-free.

## 7. Troubleshoot

| Symptom | Check |
|---|---|
| Container fails startup | Secret files exist and UID 10001 can read them; token length/config validation errors in logs |
| Port already in use | Stop the conflicting service or change only the host port mapping; update `APP_URL` for smoke checks |
| Browser returns 401 | Application token, not model provider key; recreate container after rotating it |
| Live mode returns 502 | Base URL/version path, exact model name, provider API contract, key and connectivity |
| Readiness succeeds but chat fails | Readiness is local; inspect the request ID and sanitized status, then provider-side diagnostics |
| Frequent 503 | Distinguish `Service busy` from provider unavailability; measure before raising concurrency |
| Output ends early | Inspect `finish_reason`; increase the token budget only within model/workload constraints |

For a remote VM, keep the loopback binding and use a trusted SSH tunnel for a controlled demonstration. For a public deployment, first follow [deployment decisions](../../docs/deployment-decisions.md). Do not expose this Compose file directly to the Internet by changing its bind address alone.
