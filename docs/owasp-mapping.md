# How the safeguards map to OWASP

This recipe is a small, runnable example — not a certification. But the controls it
demonstrates line up closely with two widely used OWASP lists, and it is useful to see
exactly where. This page maps each safeguard to the relevant item, states what the
recipe does *not* address, and shows where it sits among existing tools.

Lists referenced:

- **OWASP Top 10 for LLM Applications (2025)** — the LLMxx:2025 items below.
- **OWASP API Security Top 10 (2023)** — the APIxx:2023 items below.

## The deployment-layer mapping

Each row is a control you can watch fire in the [see-the-safeguards](see-the-safeguards.md)
walkthrough or the app's "Prove it yourself" panel.

| Safeguard in this recipe | OWASP LLM 2025 | OWASP API 2023 | Note |
|---|---|---|---|
| Shared bearer token, constant-time compare (`401`) | — | API2 Broken Authentication | Minimal auth; not user identity or authorization roles. |
| Body-size limit `413`, message-length limit `422`, per-minute rate limit `429`, bounded concurrency, output-token cap, bounded provider response | **LLM10 Unbounded Consumption** | API4 Unrestricted Resource Consumption | The core cost/DoS controls. Process-local, single instance. |
| Overall model-call deadline + **no hidden retries** | LLM10 Unbounded Consumption | API4 | Avoids silent repeated generation and runaway cost. |
| Strict request schema, extra fields rejected (`422`) | — | API3 Broken Object Property Level Auth / input validation | `extra="forbid"` — smuggled fields are refused, not trusted. |
| Plain-text rendering of model output (never HTML) | **LLM05 Improper Output Handling** | — | Treats model output as untrusted; no XSS/markup execution. |
| Logs omit prompts, answers, tokens, URLs | **LLM02 Sensitive Information Disclosure** | API8 Security Misconfiguration (logging) | Only request ID, status, duration are logged. |
| Operator-fixed model endpoint; client cannot choose URL or model | LLM03 Supply Chain (trusted upstream) | API7 Server-Side Request Forgery | Prevents redirecting prompts/keys to an attacker endpoint. |
| Hardened response headers (CSP, nosniff, no-referrer, no-store) + request IDs | — | API8 Security Misconfiguration | Browser hardening and traceability. |
| Non-root, read-only container, dropped capabilities, resource limits, hash-pinned dependencies | LLM03 Supply Chain | API8 Security Misconfiguration | Secure build and runtime surface. |

See [LLM10:2025 Unbounded Consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/),
[OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/), and the
[OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/).

## What this recipe deliberately does NOT cover

These belong to the *model/content* layer or to a larger production system, and are out
of scope for a single-instance deployment example:

- **Prompt injection, jailbreaks, system-prompt leakage** (LLM01, LLM07) — content-layer
  attacks. Use dedicated tools below.
- **Data/model poisoning, embedding attacks, misinformation, excessive agency** (LLM04,
  LLM06, LLM08, LLM09) — model behavior and agent design.
- **Per-user identity, authorization, distributed quotas, TLS termination, full
  observability** — production concerns documented in [deployment decisions](deployment-decisions.md).

## Where this sits among existing tools

The mapping above is the *deployment plane* — the HTTP behavior in front of the model.
It is a different layer from what the common tools test:

- **Model/content red-teaming** (prompt injection, jailbreaks, leakage): `garak`,
  Microsoft `PyRIT`, `promptfoo`, `LLM Guard`. These test the model, not the HTTP front.
- **Generic API security** (OWASP API Top 10 scanning): 42Crunch, OWASP ZAP, StackHawk,
  schemathesis. These cover auth/schema/headers generically, without the LLM-specific
  cost and output semantics.
- **Governance frameworks**: OWASP LLM Top 10, NIST AI RMF, ISO/IEC 42001 — guidance, not
  runnable endpoint probes.

This recipe's contribution is narrow and practical: it makes the **deployment-layer**
items of the OWASP LLM list (notably LLM10, LLM05, LLM02) *observable and runnable* on a
small example you can read end to end. It is a teaching reference, not a replacement for
any of the above.
