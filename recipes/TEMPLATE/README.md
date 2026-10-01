# Recipe template

This is a **skeleton, not a runnable recipe.** It lists the sections every recipe here
must cover. To add a recipe: copy this whole folder to `recipes/NN-your-recipe/`, fill in
every section below, and add the code to run it.

- **A recipe is a runnable deployment + this README + verification.** The interface is an
  API, a CLI, or `curl`. Prove its safeguards with the shared
  [readiness check](../../tools/readiness-check/README.md).
- **Complete, filled-in example:** [recipe 01](../01-ai-app/README.md) (a real recipe is
  usually richer than this minimum — extra sections are welcome).
- **How recipes are reviewed:** [GOVERNANCE.md](../../GOVERNANCE.md) — runnable, honestly
  scoped, verified, no marketing.

Delete this top block and the HTML comments when you submit.

---

<!-- Fill in everything below. -->

# NN · <Recipe title>

**Workload:** <AI application | agent workload | model serving | other>
**Maintainer / author:** <name or org — vendors welcome; same standard applies>
**Status:** <implemented and verified | partial | planned>

## What this deploys

One short paragraph: what runs, on what, and the single-sentence point of the recipe.

## Scope and boundaries

- **In scope:** <the specific thing this recipe does>
- **Not in scope:** <what it deliberately leaves out>
- **Deployment target:** <e.g. single-instance learning deployment; not a public
  multi-user service without the additions listed below>

## Prerequisites

Exact versions and accounts needed (language runtime, container runtime, GPU/driver,
cloud, CLI tools). State the hardware if it matters (GPU model, VRAM).

## Architecture

A short diagram (Mermaid) or description of the request/data path and the components.

## Run it

```bash
# exact, copy-pasteable commands to start the workload
```

Verify: <the command to call it, and what a healthy result looks like>.

## Health and readiness

Which endpoints or signals indicate liveness vs readiness, and what they do and do not
prove.

## Failure behavior

What happens on overload, upstream failure, timeout, or bad input — the actual observed
responses, not intentions. No hidden retries unless documented.

## Security and deployment decisions

The controls this recipe applies and why, each with its boundary / next step. Link
relevant items to [the OWASP mapping](../../docs/owasp-mapping.md) where applicable.

## Verification evidence

What was actually run and the result (tests, smoke checks, container build, any live
provider/hardware runs). **Mark untested integrations explicitly.** State the environment.

## Cost and performance notes

Only measured numbers, with the conditions they were measured under. No unverified
performance or cost claims.

## Stop and clean up

```bash
# exact commands to stop and remove what this recipe created
```

## Known limitations

An honest list. This is a feature of the recipe, not a weakness.
