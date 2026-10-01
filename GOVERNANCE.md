# Governance

This project is a **vendor-neutral, runnable cookbook for deploying AI workloads**.
Its value depends entirely on being trustworthy, so governance exists to protect that.

## Principles

1. **Runnable over aspirational.** Every recipe must actually run, with exact steps,
   health checks, and verification evidence. Untested integrations are marked as such.
2. **Trade-offs made explicit.** A recipe states its deployment scope, failure behavior,
   and what it does *not* cover. No unqualified "production ready" claims.
3. **Vendor-neutral.** Recipes may use or feature any tool, cloud, or inference server —
   including a vendor's own. They are held to the same standard regardless of who wrote
   them: real verification, honest limitations, and **no marketing language**. There is
   no paid placement, and sponsorship never buys a different review.
4. **Small enough to inspect.** Changes stay reviewable. Evidence beats assertion.

## Roles

- **Maintainers** review and merge contributions, curate the recipe catalog, and uphold
  the principles above. The project starts with a single maintainer; additional
  maintainers are added by invitation from existing maintainers, based on sustained,
  high-quality contribution.
- **Contributors** propose recipes, fixes, and improvements via pull request. Anyone can
  contribute, including vendors publishing a recipe for their own tool.

## How decisions are made

- Routine changes: a maintainer reviews and merges once CI and the recipe checklist pass.
- Larger or contested changes (new recipe *categories*, structural changes, policy):
  opened as an issue for discussion first; maintainers seek rough consensus and decide.
- A recipe is accepted when it is runnable, verified, honestly scoped, and free of
  marketing. A recipe is rejected or sent back when it overclaims, cannot be reproduced,
  or reads as a vendor advertisement.

## Vendor-authored recipes

Vendors are welcome to publish recipes for their tools. To keep trust intact:

- The recipe uses the standard [recipe template](recipes/TEMPLATE/README.md) and passes
  the same checks as any other.
- It documents real limitations and failure modes, not just the happy path.
- Comparative or "best" claims require reproducible evidence, or they are removed.
- A `works-with` or `verified` label, when introduced, reflects a maintainer-run check —
  not a commercial relationship.

This document is intentionally light and will grow only as the project does.
