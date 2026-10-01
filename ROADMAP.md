# Roadmap

This project grows into a **vendor-neutral, runnable cookbook for deploying AI workloads**.
The items below are direction, not promises or delivery dates. A recipe ships only when it
actually runs and is verified.

## Now — a credible, runnable hub

- **Recipe 01 (AI application)** — available; container build, smoke, and non-root/read-only
  checks pass in CI.
- **Community foundations** — governance, recipe template, contribution and issue
  templates, code of conduct. *(In place.)*
- **Readiness check — available.** A small, dependency-free
  [tool](tools/readiness-check/README.md) that probes any recipe's endpoint and reports
  which safeguards are present, and works as a CI gate — the runnable hook that makes the
  cookbook more than documentation, and how every recipe shows its safeguards. Next:
  per-recipe profiles for non-chat shapes.

## Next — recipes by workload

- **AI applications:** a TLS-terminated ingress example; a reproducible load-test recipe
  with recorded workload parameters.
- **Agent workloads:** a queue-backed worker with persisted task state, bounded retries,
  recovery exercises, and idempotent mock side effects. Document at-least-once delivery and
  the action/checkpoint boundary honestly; no unsupported "exactly once" claims.
- **Model serving:** a GPU model-server recipe with explicit model/license/hardware
  requirements. Measure latency and memory under representative context lengths and
  concurrency, and publish the hardware, versions, and test conditions with every number.

## Then — community and contributions

- Lower the bar to contribute: good-first-issue recipe requests and worked examples.
- Welcome **vendor-authored recipes** under the same standard — runnable, verified,
  honestly scoped, no marketing. The [recipe template](recipes/TEMPLATE/README.md) is the
  contribution slot.
- A `works-with` / `verified` label that reflects a maintainer-run check, never a
  commercial relationship.

## How to help

Start with a focused issue describing a workload and a reproducible need, or propose a
recipe from the template. Keep each recipe independently runnable. Broad vendor support or
a large infrastructure stack is not a prerequisite for a useful contribution.
