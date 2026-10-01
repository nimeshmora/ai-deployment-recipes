# Contributing

Thanks for helping make AI deployments easier to understand.

For recipe 01, use Python 3.12, install `requirements-dev.txt` with `--require-hashes`, and run `pytest`, `ruff check .`, and `ruff format --check .` from its directory. Run the container smoke check when changing Docker or Compose configuration. CI must pass before merging.

A useful pull request explains the problem, the change, what was tested, and remaining limitations. Add behavioral tests for new failure handling. Do not add credentials, real prompts containing private data, or unverified performance claims.

Each new recipe should include exact prerequisites, architecture, start/stop instructions, health checks, failure behavior, security/deployment scope, verification evidence, and cleanup steps. Mark untested integrations explicitly.

Maintain Python locks from their `.in` files and review the final image separately. Keep changes small enough to inspect. Contributions are provided under the repository's MIT license.
