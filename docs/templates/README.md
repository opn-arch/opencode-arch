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

## Cost & requirements

`opencode-arch extract .` runs a full architecture extraction on every
invocation. That is not free — plan for it before you install these
templates.

- **LLM calls.** Extraction drives a frontier LLM through the 10-stage
  pipeline. Expect several thousand tokens per run on small repos and
  tens of thousands on medium repos. Configure your provider credentials
  (typically `ANTHROPIC_API_KEY` or the equivalent for your policy) in
  the environment where the hook / workflow runs.
- **Runtime.** Full extraction on a small repo takes ~1–2 minutes and
  scales roughly linearly with module count. The pre-commit hook runs
  synchronously; contributors will feel this on every commit.
- **Pre-commit failure mode.** By default the hook is warning-only:
  extraction failures (network hiccups, missing keys, LLM errors) log a
  warning and let the commit through. Export `OPENCODE_ARCH_STRICT=1` to
  make failures abort the commit instead. Fail-closed by default was
  rejected because it trains contributors to reach for `--no-verify`.
- **CI secrets.** `architecture-refresh.yml` needs the same LLM
  credentials exposed as GitHub Actions secrets (e.g.
  `ANTHROPIC_API_KEY`). Without them the workflow will fail on every
  run. Wire the secret into the workflow env before enabling it on
  `main`.
- **Incremental refresh.** These templates always run a full extract.
  A scoped `refresh --changed` command is on the roadmap; swap to it
  when it lands to cut per-commit cost.
