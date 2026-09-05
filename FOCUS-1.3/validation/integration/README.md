# Integration rehearsal with the shared core

This is a temporary local combination, not a merge into upstream main.

- FOCUS 1.2 code: `e14921a3ba8d5f75a7b899d878e372999482ba9a`.
- FOCUS 1.3 code, already based on that 1.2 commit: `15c6ce4c70ce9dd3c3bf4fb62b5aec4874b8d761`.
- Model-driven workflow PR #5: `4fe60d96737ea06c64851f3a0b2bcd675125b980`.
- Local tested merge: `33de05ad60ade5e3dee2c3b2c292a9356a2847af`.

The following publication commit adds only this integration evidence. Generation
sources and CSVs are identical to the tested code above; their SHA-256 hashes,
commands, exit codes and raw-log hashes are recorded in `result.json`.

Both acceptance suites, the 23 existing regressions, six shared-core tests,
540 frozen output cases, statistics and complete saved-validator checks pass.
The four Windows/Linux and Python 3.11/3.12 runs are recorded separately under
`../refactor/`. The nine official provider reports remain unchanged in rule states
and violation counts. This does not claim execution or validation of PR #5's
generic generation workflow: its tooling, workflows and three generic CSV files
are preserved exactly (Git blob inventory in `result.json`).

## Reproduce

Use a disposable clone and fetch the current provider branches plus PR #5:

```bash
git fetch https://github.com/guymano/FOCUS-Sample-Data.git add-focus-1-2-provider-samples add-focus-1-3-provider-samples
git fetch https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data.git refs/pull/5/head
git switch --detach 15c6ce4c70ce9dd3c3bf4fb62b5aec4874b8d761
git switch -c codex/shared-integration-rehearsal
git merge --no-ff 4fe60d96737ea06c64851f3a0b2bcd675125b980
```

Resolve `.gitignore` and both dataset READMEs with the adjacent `combined-*`
texts, then stage those three paths and complete the local merge. Both provider
versions already share `generators/README.md`; its combined text is supplied too.
These resolutions target the recorded commits and must be reviewed against any
newer upstream changes. Run:

```bash
python generators/run_regression_checks.py --output-dir /path/to/integration-results
```

The previous rehearsal is preserved in `before-shared/`. Root-level older
`*-evidence-check.log` files also belong to that historical rehearsal; the new
runner's authoritative logs are those referenced by the current `result.json`.

## Actual upstream integration remains pending

After PR #6 merges, fetch the actual accepted upstream main, rebase PR #7 onto it,
reconcile any newer PR #5 changes, and rerun both versions' checks and official
validation. Keep the integration review thread open until that rebase is published.
No upstream PR has been merged by this rehearsal.
