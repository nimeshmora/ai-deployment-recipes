# Publish the first GitHub release

This package has not been pushed to GitHub. The owner/account and destination repository have not been selected.

1. Extract the archive and inspect `README.md` and `docs/verification.md`.
2. Create an empty GitHub repository named `ai-deployment-recipes`. Do not generate another README or license.
3. From the extracted repository root:

```bash
git init -b main
git add .
git diff --cached --stat
# Verify .secrets/, .env, virtual environments and caches are absent from staged files.
git status --short
git commit -m "Add first AI application deployment recipe"
git remote add origin https://github.com/YOUR-USERNAME/ai-deployment-recipes.git
git push -u origin main
```

4. Let the GitHub Actions workflow finish. Fix any failures before tagging a release. Actions availability and artifact downloads depend on GitHub and your account settings.
5. Complete the container/live-provider checks in the verification record and update the record with actual results; do not mark unexecuted checks as passed.
6. Enable private vulnerability reporting in repository security settings, and configure branch protection as appropriate.
7. Tag `v0.1.0` only after reviewing the gates above. Describe it as the initial application recipe with agents/model serving planned.

Suggested repository description:

> Small, runnable AI deployment recipes for applications, agents, and models. Starting with a bounded, containerized text assistant.

Suggested topics: `ai-infrastructure`, `ai-deployment`, `docker`, `fastapi`, `llm`, `devops`.

No CI badges, deployment counts, benchmarks, customer claims, or test environments should be advertised unless backed by actual results.
