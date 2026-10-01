![AI Deployment Recipes — a runnable cookbook; prove every safeguard with the readiness check](docs/assets/banner.svg)

# AI Deployment Recipes

### Find your workload. Run a recipe. Understand the deployment.

**New here? This is for you too.** "Deploying" an AI app just means *actually running it as a real service people can use* — not only getting a model to reply once on your laptop, but putting it online so it stays up, can't be abused, and won't quietly run up a huge bill. That part is genuinely hard, and most tutorials skip it.

This project is a **cookbook for exactly that.** Each *recipe* is a small, real AI service you can **run yourself in a few minutes**, already set up the careful way — a password to get in, limits so no one can abuse it, timeouts, and a locked-down container — with plain-language notes on *why* each piece is there.

You don't need to be an expert, or even have an AI account. The first recipe runs with **no API key and no cost**: it replies with a fixed message so you can watch a real, safe deployment work before plugging in an actual model. If you can install Docker and copy a few commands, you're in.

> In one line: **a vendor-neutral, runnable cookbook for deploying AI workloads** — apps, agents, and model serving — with the safeguards built in and the trade-offs made explicit.

Maintained by Nimesha Jinarajadasa. Contributions — including vendor-authored recipes — are welcome; see [Contribute a recipe](#contribute-a-recipe).

## What you get, and how to use it

Whether you're about to put an AI service online or just want to understand what that safely takes, here's the path — about 10 minutes:

1. **Run a safe AI service.** Four commands ([below](#run-recipe-01)) start recipe 01 on your machine. Free, no API key.
2. **See it work.** One `curl` returns a reply.
3. **Prove it's safe.** The [readiness check](tools/readiness-check/README.md) reports which safeguards are present (`8/8`) — the auth, limits, and timeouts that stop abuse and runaway cost.
4. **Understand the choices.** [Deployment decisions](docs/deployment-decisions.md) explains each safeguard in plain words, with its limits and what you'd add before going public.
5. **Make it yours.** Start from recipe 01's patterns for your own service, and re-run the readiness check as you adapt it, to catch anything you dropped.

You walk away with a **hardened, copyable starting point** and a **tool to verify** a deployment has the safeguards most tutorials skip — the difference between "a model replied" and "a service I can safely put online."

## Recipes

| Workload | Recipe | Status |
|---|---|---|
| AI applications | [01 · Containerized text assistant](recipes/01-ai-app/README.md) | **Available.** App tests, container build/smoke, and non-root/read-only checks pass in CI. Live-provider run still pending. |
| Agent workloads | Durable tasks, retries, and recovery | Planned |
| Model serving | GPU inference, capacity, and overload handling | Planned |

See the [roadmap](ROADMAP.md) for what's next and how it's prioritized.

## Run recipe 01

Prerequisites: **Python 3.12+** (setup/smoke scripts) and **Docker with Compose v2**.

```bash
cd recipes/01-ai-app
python3 scripts/init_local.py
cp .env.example .env            # PowerShell: Copy-Item .env.example .env
docker compose up --build -d --wait
python3 scripts/smoke.py
```

It's an **API, not a web page.** Call it — in **mock mode** (the default) it returns a fixed reply and calls no model, so no API key and no cost:

```bash
curl -s http://localhost:8000/api/chat \
  -H "Authorization: Bearer $(cat .secrets/app_token)" -H 'Content-Type: application/json' \
  -d '{"message": "Hello"}'
```

Then prove its safeguards with the shared readiness tool:

```bash
python3 ../../tools/readiness-check/readiness_check.py http://localhost:8000 --token "$(cat .secrets/app_token)"
```

Stop with `docker compose down`. Live mode, Python-only development, and troubleshooting are in the [recipe README](recipes/01-ai-app/README.md).

## What recipe 01 shows

Recipe 01 is a stateless, single-turn text assistant (an HTTP API, no UI) that demonstrates the deployment safeguards every recipe here is held to:

- shared-token authentication; request-body, message, rate, and concurrency limits
- upstream timeouts plus an overall deadline; no hidden retries; bounded provider responses
- separate liveness/readiness; request IDs; logs that omit prompts, answers, and secrets
- non-root, read-only container with dropped capabilities and resource limits
- hash-pinned dependencies, automated tests, and CI with a container smoke test

You can **prove them yourself** — run the [readiness check](tools/readiness-check/README.md) against the endpoint, or trigger each one by hand in the [see-the-safeguards](docs/see-the-safeguards.md) walkthrough — and see **[how they map to the OWASP LLM Top 10 & API Security](docs/owasp-mapping.md)**.

The scope is stated plainly: this targets a **single-instance learning deployment or internal prototype**, not a public multi-user service. [Deployment decisions](docs/deployment-decisions.md) pairs each choice with its boundary and next step; the [verification record](docs/verification.md) states exactly what was and wasn't tested.

<details>
<summary>Architecture</summary>

```mermaid
flowchart TD
    B[API client] --> A[Authentication and input limits]
    A --> G[Rate and concurrency admission]
    G --> M[Mock response]
    G --> H[Bounded HTTP model adapter]
    H --> P[Configured model endpoint]
    L[Health probes] --> S[Local process and readiness]
```

The model endpoint belongs to the operator; users cannot choose a URL or model through a request.
</details>

## Contribute a recipe

The cookbook grows by workload. Anyone can add a recipe — **including vendors publishing one for their own tool** — held to the same standard: it must actually run, document its failure behavior and limitations, include verification evidence, and carry no marketing. Start from the [recipe template](recipes/TEMPLATE/README.md); [governance](GOVERNANCE.md) explains how recipes are reviewed and why neutrality is protected.

**No UI to build.** A recipe is a runnable deployment + a README + verification — an API or CLI, not a web page (recipe 01 included). Safeguards are shown via the shared [readiness check](tools/readiness-check/README.md).

## Docs

- [Docs index](docs/README.md) — what each document is, and a reading order
- [Readiness check](tools/readiness-check/README.md) — a tool that probes any recipe's endpoint for safeguards
- [Recipe 01 — run, deploy, verify, troubleshoot](recipes/01-ai-app/README.md)
- [See the safeguards yourself](docs/see-the-safeguards.md) · [OWASP mapping](docs/owasp-mapping.md)
- [Deployment decisions](docs/deployment-decisions.md) · [Verification record](docs/verification.md)
- [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Governance](GOVERNANCE.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Security](SECURITY.md) · [License: MIT](LICENSE)
