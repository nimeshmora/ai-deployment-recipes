# Roadmap

We are starting simple: one application, one process, and deployment decisions that can be inspected. The project will grow through tested examples. Planned work below is not included in v0.1.0, and no delivery dates are promised.

## First: strengthen the baseline

- Complete the container and live-provider validation matrix and publish results.
- Add a separately reviewed TLS ingress deployment example.
- Add a reproducible load-test recipe with recorded workload parameters.

## Next: agent workloads

A queue-backed worker with persisted task state, bounded retries, recovery exercises, and idempotent mock side effects. Document at-least-once delivery and the action/checkpoint boundary; avoid unsupported “exactly once” claims.

## Then: model serving

A GPU model-server recipe with explicit model/license/hardware requirements. Measure memory and latency under representative context lengths and concurrency. Publish hardware, software versions, prompts and test conditions with every result.

## Contributions

Start with a focused issue describing the workload and a reproducible need. Keep each recipe independently runnable. Broad vendor support or a large infrastructure stack is not a prerequisite for a useful contribution.
