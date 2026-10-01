<!--
Copy this folder to recipes/NN-your-recipe/ and fill every section.
A recipe is accepted when it is runnable, verified, honestly scoped, and free of
marketing. Delete these comments before submitting. See ../../GOVERNANCE.md.
-->

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

Open / verify: <URL or command and what a healthy result looks like>.

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
