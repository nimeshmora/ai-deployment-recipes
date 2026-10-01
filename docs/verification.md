# Verification record — v0.1.0 candidate

Prepared 2026-10-01. Results apply to the supplied source snapshot, not all deployment environments or future dependency updates.

| Check | Result | Scope |
|---|---|---|
| Application tests | PASS — 42 tests | Python 3.12.14, Linux; application and controlled provider fixtures |
| Ruff lint and format | PASS | Application, scripts, tests |
| JavaScript syntax | PASS | Node syntax check of `app/static/app.js` |
| HTTP smoke, mock mode | PASS | Real Uvicorn process, liveness/readiness/authenticated completion over loopback HTTP |
| HTTP smoke, live adapter | PASS against a local fixture | Real HTTP fixture for the supported Chat Completions contract; **not** a real model/provider |
| Process termination | PASS | Idle Uvicorn process terminates cleanly after smoke checks; in-flight shutdown load not tested |
| Runtime dependency audit | PASS — no known vulnerabilities reported | `pip-audit 2.10.1`, locked runtime requirements; not a guarantee of absence of vulnerabilities |
| Dependency artifact hashes | Included | Runtime and development locks contain hashes; installation tested with hash enforcement |
| GitHub Action references | Checked | Checkout v4.2.2 and setup-python v5.6.0 SHA values checked against upstream tags |
| Container build/runtime | NOT RUN | Docker is not installed in the authoring environment; CI includes build, smoke, non-root and read-only checks |
| GitHub Actions execution | NOT RUN | Repository has not been published |
| External live provider/model | NOT RUN | No provider credentials or real model endpoint supplied |
| Browser visual/interaction check | NOT RUN | Browser binary unavailable; attempted installation failed. HTML/CSS and JavaScript inspected, HTTP assets checked by tests. |
| Load/cost/answer-quality evaluation | NOT RUN | No performance, spending, or quality claims are made |
| GPU behavior | NOT APPLICABLE | GPU-serving recipe is planned, not included |

## Behaviors exercised by automated tests

Authentication; mock response labeling; health/static endpoints; response security headers; invalid/oversized input; fixed-window limits and reset; exact upstream request payload; provider 429/5xx, rejection and redirects; malformed/oversized/compressed responses; transport errors; overall timeout; immediate concurrency rejection; health access while a model call is active; concurrency-slot release after timeout/cancellation; redacted logs; invalid configuration; incoming-body timeout.

## Complete before advertising a validated container release

1. Run the included GitHub Actions workflow, or equivalent Docker checks locally, on the intended architecture.
2. Run the browser flow in mock mode, including an invalid token and a valid request.
3. For any named provider support claim, record provider/model/API version and run a live smoke test with that exact integration.
4. Scan the final image and record its digest. The Python base image uses a moving tag in this initial recipe.
5. Re-run tests after changing configuration, dependencies, or implementation. Record limitations rather than replacing them with an unqualified “production ready” label.
