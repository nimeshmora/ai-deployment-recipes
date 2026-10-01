![AI Deployment Recipes — deploy an AI app you can actually explain](docs/assets/banner.jpg)

# AI Deployment Recipes

### Find your workload. Run a recipe. Understand the deployment.

A **vendor-neutral, runnable cookbook for deploying AI workloads** — AI applications, agent workloads, and model serving. Each recipe is a small deployment you can actually run, with the safeguards built in and the trade-offs made explicit.

Most AI examples stop at *calling a model*. The hard part is everything around it — authentication, limits, timeouts, hardened containers, health checks, failure behavior — the gap between "I got a model running" and "I run it in production." These recipes fill that gap honestly: every recipe states what it does, how it fails, what it does **not** cover, and the evidence that it was actually tested.

Maintained by Nimesha Jinarajadasa. Contributions — including vendor-authored recipes — are welcome; see [Contribute a recipe](#contribute-a-recipe).

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

Open **http://localhost:8000**, paste the token from `.secrets/app_token`, and send a message. In **mock mode** (the default) it returns a fixed response and calls no model — so it runs with no API key and no cost. Stop with `docker compose down`. Live mode, Python-only development, and troubleshooting are in the [recipe README](recipes/01-ai-app/README.md).

## What recipe 01 shows

Recipe 01 is a stateless, single-turn text assistant (browser UI + API) that demonstrates the deployment safeguards every recipe here is held to:

- shared-token authentication; request-body, message, rate, and concurrency limits
- upstream timeouts plus an overall deadline; no hidden retries; bounded provider responses
- separate liveness/readiness; request IDs; logs that omit prompts, answers, and secrets
- non-root, read-only container with dropped capabilities and resource limits
- hash-pinned dependencies, automated tests, and CI with a container smoke test

You can **[watch each safeguard fire yourself](docs/see-the-safeguards.md)** (or in the app's "Prove it yourself" panel), and see **[how they map to the OWASP LLM Top 10 & API Security](docs/owasp-mapping.md)**.

The scope is stated plainly: this targets a **single-instance learning deployment or internal prototype**, not a public multi-user service. [Deployment decisions](docs/deployment-decisions.md) pairs each choice with its boundary and next step; the [verification record](docs/verification.md) states exactly what was and wasn't tested.

<details>
<summary>Architecture</summary>

```mermaid
flowchart TD
    B[Browser or API client] --> A[Authentication and input limits]
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

## Docs

- [Docs index](docs/README.md) — what each document is, and a reading order
- [Recipe 01 — run, deploy, verify, troubleshoot](recipes/01-ai-app/README.md)
- [See the safeguards yourself](docs/see-the-safeguards.md) · [OWASP mapping](docs/owasp-mapping.md)
- [Deployment decisions](docs/deployment-decisions.md) · [Verification record](docs/verification.md)
- [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Governance](GOVERNANCE.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Security](SECURITY.md) · [License: MIT](LICENSE)
