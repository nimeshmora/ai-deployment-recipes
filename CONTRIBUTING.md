# Contributing

Thanks for helping make AI deployments easier to understand. This is a vendor-neutral,
runnable cookbook — see [GOVERNANCE.md](GOVERNANCE.md) for the principles and how recipes
are reviewed.

## Repository layout

```
README.md              Start here: what this is, how to run the first recipe
ROADMAP.md             Planned recipes (apps → agents → model serving)
GOVERNANCE.md          Principles, roles, how recipes are reviewed
recipes/
  TEMPLATE/            Copy this to start a new recipe
  01-ai-app/           Recipe 01 — containerized text assistant (reference example)
tools/
  readiness-check/     Probe any recipe's endpoint for safeguards (CI-friendly)
docs/
  deployment-decisions.md   Decisions and public-service requirements
  see-the-safeguards.md     Run each safeguard yourself
  owasp-mapping.md          How safeguards map to OWASP
  verification.md           What was actually tested
  release-checklist.md      Maintainer gates before tagging
.github/                 CI workflow, issue/PR templates, Dependabot
```

Cross-cutting docs live in `docs/`. Anything specific to one recipe lives inside that
recipe's folder.

## Add a recipe (the main contribution path)

1. Copy `recipes/TEMPLATE/` to `recipes/NN-your-recipe/` (next free number).
2. Fill **every** section of its `README.md`, and add the code to run it.
3. Make sure it actually runs from the exact commands you wrote, including stop/cleanup.
4. Document failure behavior, verification evidence, and **known limitations** honestly.
   Mark untested integrations as untested.
5. Open a pull request (the template lists the checklist).

**No UI required.** A recipe is a runnable deployment + a filled-in README + verification.
Many recipes (model serving, agent workloads) have no browser page at all — the interface
is an API, a CLI, or `curl`. Recipe 01's web page is a flagship extra, not the bar every
recipe must clear. Showing a recipe's safeguards is done consistently through its README
and the shared readiness check, not a bespoke UI.

Vendors are welcome to add a recipe for their own tool — held to the same standard:
runnable, honestly scoped, verified, and free of marketing.

## Develop and test recipe 01

From `recipes/01-ai-app/`, using Python 3.12:

```bash
python -m pip install --require-hashes -r requirements-dev.txt
pytest -q
ruff check .
ruff format --check .
```

Run the container smoke check when changing Docker or Compose configuration. **CI must
pass before merging.** Maintain Python locks from their `.in` files; review the final
image separately.

## Pull request expectations

A useful PR explains the problem, the change, what was tested, and remaining limitations.
Add behavioral tests for new failure handling. Keep changes small enough to inspect.

Do **not** add credentials, real prompts containing private data, or unverified
performance claims.

Contributions are provided under the repository's MIT license.
