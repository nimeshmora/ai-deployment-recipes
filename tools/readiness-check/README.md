# Readiness check

A small, dependency-free tool that probes a running AI service and reports which
deployment safeguards are present — the shared, portable version of recipe 01's
"what protects this deployment" panel. Point it at **any** recipe's endpoint.

## Use it

Start a recipe (for example [recipe 01](../../recipes/01-ai-app/README.md)), then:

```bash
python3 tools/readiness-check/readiness_check.py http://localhost:8000 \
  --token "$(cat recipes/01-ai-app/.secrets/app_token)"
```

Output:

```
  PASS  auth required          [API2]   no token -> HTTP 401 (want 401)
  PASS  hardened headers       [API8]   all present
  PASS  content-type enforced  [API8]   text/plain -> 415
  PASS  strict schema          [API3]   unknown field -> 422
  PASS  oversized rejected     [LLM10]  ~20 KB -> 413
  PASS  rate limited           [LLM10]  30 ok, 5 throttled (429)

  Score: 8/8 safeguards present
```

Exit code is non-zero if any checked safeguard is missing, so it works as a CI gate.
Without `--token`, the token-gated checks skip (they don't fail).

## What it checks

Only what is observable from outside the service: authentication, content-type
enforcement, a strict request schema, oversized-body rejection, rate limiting,
hardened response headers, and health endpoints. Each maps to the
[OWASP mapping](../../docs/owasp-mapping.md).

## What it does NOT check

Things you can't see from a client — **redacted logs, non-root/read-only container,
pinned dependencies** — which the recipe and CI verify instead. This is a quick signal,
not a certification.

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--token` | empty | App bearer token; unlocks the token-gated checks |
| `--path` | `/api/chat` | The chat/inference path to probe |
| `--health` | `/health/live,/health/ready` | Health endpoints to check |
| `--rpm` | `30` | Expected per-minute budget (sizes the rate-limit burst) |
| `--no-rate` | off | Skip the rate-limit check (it spends the minute's budget) |

It assumes a recipe-01-style JSON chat endpoint; use `--path` / `--health` for other
shapes. Broader per-recipe profiles are planned.
