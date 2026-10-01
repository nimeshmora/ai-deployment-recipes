# Deployment decisions

This release makes a few controls concrete while keeping the application small. “Best practice” depends on exposure, data, traffic, and reliability requirements; use the decisions below as a reviewable baseline.

| Decision | Reason | Boundary / next step |
|---|---|---|
| One process, one replica | Process-local admission counters stay understandable | Multiple workers/replicas multiply these limits. Move admission/quotas to a shared system before scaling. |
| Shared application token | Minimal authentication without an identity stack | Not user identity, authorization roles, sessions, or individual revocation. Add OIDC or another appropriate identity layer for real users. |
| Loopback-only published port | Local demo defaults to host-local access | Public ingress requires TLS and access control; an SSH tunnel is suitable for a controlled personal demo. |
| Trusted, fixed model endpoint | Clients cannot choose destinations or arbitrarily spend on other models | Validate operator configuration, control outbound egress and provider credentials. |
| No automatic retries | Avoid hidden repeated generation and costs | Add bounded retries with jitter only for selected errors and known semantics. |
| Request and response bounds | Constrain application memory/work per accepted request | Not a complete network DoS defense; use ingress/header/connection limits and infrastructure controls. |
| Plain-text model output | Model output is untrusted | Returned verbatim as a JSON string; no tools, shell execution, database access, or rich rendering in this recipe. |
| Separate local health signals | Provider outages should not automatically trigger process restart loops | Monitor upstream availability separately; route-level readiness policies depend on the deployment. |
| Read-only, non-root container | Reduce writable surface and ambient privileges | Not a sandbox for hostile code. The image itself remains readable and network egress remains available. |
| File-mounted secrets | Keep secrets out of build layers and checked-in configuration | Local Compose files are not an encrypted vault; protect the host and use a secret manager when deployed. |
| Locked dependency artifacts | Make reviewed Python package selections repeatable | Base image tag still moves. Pin a reviewed base digest, scan/rebuild and record image digest for releases. |

## Before serving public, multi-user traffic

- Terminate HTTPS at a managed ingress or reviewed proxy. Set suitable body/header/connection limits and upstream deadlines. Avoid query-string credentials and review access logs.
- Establish user identity, authorization, distributed per-user quotas, and spend monitoring. Token output caps and request limits are not a hard currency budget.
- Evaluate model quality, sensitive-data handling, provider retention, abuse scenarios, and safe output handling for the actual application.
- Define latency/error objectives; collect metrics/traces and alert on symptoms. Logs in this repository are a starting point, not a complete observability stack.
- Measure representative input/output lengths, traffic patterns, latency distributions and resource usage before changing concurrency or replica count.
- Build from a reviewed commit; scan dependencies and the final image, pin the base image by digest, publish an immutable application image, and record rollback instructions.
- Test termination, provider outage, malformed replies and saturation in staging. Decide how to drain traffic and roll out changes without relying on Compose for high availability.
- Use managed secrets with explicit rotation/revocation. This application reads secrets at startup, so rotate through controlled container replacement.

## Primary references

These describe the mechanisms used; they do not certify this project.

- [FastAPI container deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker Compose service controls](https://docs.docker.com/reference/compose-file/services/)
- [Docker Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/)
- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/)
- [HTTPX connection limits](https://www.python-httpx.org/advanced/resource-limits/)
- [Uvicorn settings](https://www.uvicorn.org/settings/)
- [Uvicorn server behavior](https://www.uvicorn.org/server-behavior/)
- [vLLM compatible API contract](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)
- [uv requirements locking](https://docs.astral.sh/uv/pip/compile/)
