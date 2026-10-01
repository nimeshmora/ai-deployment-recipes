# Release checklist

The repository is published at <https://github.com/nimeshmora/ai-deployment-recipes>.
Use this list before tagging a release. The goal is that a tag never claims more than was
actually verified.

## Before tagging

1. **CI is green** on `main` (lint, format, tests, container build, non-root/read-only
   checks, smoke test).
2. **Verification record is honest.** Update [verification.md](verification.md) with
   actual results. Do not mark unexecuted checks as passed; record limitations instead.
3. **For any named provider/hardware support claim**, record the exact provider, model,
   API version, or GPU, and the result of a real run with that integration.
4. **Scan the final container** and record its image digest. Replace moving base-image
   tags with a pinned digest for a release build.
5. **Dependencies reviewed.** Dependency updates enabled; advisory results inspected;
   Python locks regenerated from their `.in` files if changed.
6. **Secrets check.** Confirm `.secrets/`, `.env`, virtual environments, and caches are
   absent from the repository (`git status --short` and a staged-file review).

## Repository security settings

- Enable **private vulnerability reporting** (Settings → Security).
- Configure **branch protection / rulesets** on `main`: block force pushes and deletions.
- Keep **Dependabot** enabled; triage its PRs (rebase or merge on their merits).

## Tagging

- Tag only after the gates above pass.
- Describe the release honestly: what is implemented and verified, and what is planned.
- Rotate any credential that was exposed accidentally at any point.

Suggested repository topics: `ai-infrastructure`, `ai-deployment`, `docker`, `fastapi`,
`llm`, `devops`, `kubernetes`.
