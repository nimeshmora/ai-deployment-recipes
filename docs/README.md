# Docs

Background and evidence for the recipes. If you're new, start with the main
[README](../README.md), then [run recipe 01](../recipes/01-ai-app/README.md). Come here
when you want the *why* and the proof.

## What's in here

| Doc | What it is | Read it when |
|---|---|---|
| [see-the-safeguards.md](see-the-safeguards.md) | Hands-on: trigger each safeguard yourself and watch it block a bad request | You want proof the controls work, not just claims |
| [deployment-decisions.md](deployment-decisions.md) | Every deployment choice paired with its reason and its "next step" for real use | You want to know *why* a safeguard is there, or what's needed before going public |
| [owasp-mapping.md](owasp-mapping.md) | How each safeguard maps to the OWASP LLM Top 10 & API Security — and what's out of scope | You're checking this against known standards |
| [verification.md](verification.md) | Exactly what was tested, and what was not | You want to trust the claims |
| [release-checklist.md](release-checklist.md) | Maintainer gates before tagging a release | You maintain the project |

`runtime-dependency-audit.json` is raw scan output, linked as evidence from the
verification record.

To check a running recipe's safeguards automatically, use the
[readiness check](../tools/readiness-check/README.md) tool.

## Suggested reading order (newcomer)

1. [Main README](../README.md) — what this project is
2. [Recipe 01](../recipes/01-ai-app/README.md) — run a real deployment
3. [See the safeguards](see-the-safeguards.md) — watch the controls act
4. [Deployment decisions](deployment-decisions.md) — understand each choice
5. [OWASP mapping](owasp-mapping.md) — place it against the standards
