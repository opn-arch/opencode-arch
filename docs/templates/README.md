# Architecture Refresh Templates (opt-in)

These templates are **opt-in** — they are not installed automatically by
`pip install opencode-arch`. Copy them into your repository when you want
architecture-model refresh to run on commits or in CI.

## Files

- `pre-commit.sh` — Git pre-commit hook. When staged changes touch
  `.py`, `.ts`, `.tsx`, or `.js` files, invokes `opencode-arch extract .`
  to refresh the architecture model. Aborts the commit if extraction fails.
- `architecture-refresh.yml` — GitHub Actions workflow. Runs
  `opencode-arch extract .` on pushes to `main` and on pull requests,
  and uploads `.architecture/lifecycle/artifacts/` as a build artifact.

## Install

Pre-commit hook (per clone; git does not track `.git/hooks/`):

```bash
cp docs/templates/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

GitHub Actions workflow:

```bash
mkdir -p .github/workflows
cp docs/templates/architecture-refresh.yml .github/workflows/
```

## Notes

- Both templates call the `opencode-arch` CLI (installed by
  `pip install opencode-arch`); the hook no-ops with a warning if the
  binary is missing.
- No incremental `refresh --changed` subcommand exists yet, so both
  templates invoke a full `extract`. Swap the command when a scoped
  refresh lands.
