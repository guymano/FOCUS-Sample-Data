# Integration rehearsal

This records a local rehearsal, not an upstream merge or a completed rebase.
Provider suite commits: 1.2 `977f8184411ae332ee5d384ae34556281e0e3b10`, 1.3 `4bdd6089a5bc02bdf95271753fb3ed00d7f09b5f`.
Model-driven workflow PR #5: `4fe60d96737ea06c64851f3a0b2bcd675125b980`.
The final PR #7 evidence-only commit adds this directory without changing tested code or data.

The 1.2/1.3 combination conflicted only in `generators/README.md`. Adding #5
conflicted in `.gitignore` and both dataset READMEs. The prepared texts retain both
provider versions and the model-driven instructions. All #5 tooling, workflows and
three generic CSV examples are byte-identical to its head. Provider scripts and
CSVs are likewise identical to the two reviewed branches (hashes in result.json).

The rehearsal initially exposed the validation wrapper globbing unrelated generic
CSVs. Both wrappers now select their explicit provider file inventory and reject a
missing provider file; a regression exercises coexistence with unrelated CSVs.
The final combination passes both acceptance suites, 10 + 13 regression tests,
both statistics checks, and both complete saved-report checks. Logs and commands
are in result.json. Live official-validator reports are those already recorded for
the identical nine provider CSVs, not a claimed new run of #5's generic workflow.

## Reproduce the preparation

In a disposable clone, fetch the three commits above from their PR branches:

```bash
git fetch https://github.com/guymano/FOCUS-Sample-Data.git add-focus-1-2-provider-samples add-focus-1-3-provider-samples
git fetch https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data.git refs/pull/5/head
git switch --detach 4bdd6089a5bc02bdf95271753fb3ed00d7f09b5f
git switch -c codex/integration-rehearsal
git merge --no-ff 977f8184411ae332ee5d384ae34556281e0e3b10
```

Resolve generators/README.md with the adjacent combined-generators-README.md.txt,
stage that path and complete the merge. Then merge the recorded #5 commit and
resolve the three paths with the adjacent combined-gitignore.txt and combined
dataset README texts. Stage only those conflict resolutions and complete that
local merge. The prepared files can be copied from this evidence directory in the
published PR; they are templates for the recorded commits, not an automatic patch
for future upstream changes. Run every command listed in result.json from the root.

## Actual integration still pending

After PR #6 is merged, fetch the actual upstream main and rebase PR #7 on that
accepted history. Reconcile these prepared sections with any newer #5/upstream
changes, preserve both generator families and their examples, and rerun both
versions' checks and official validation. Resolve the integration review thread
only after that real rebase is published. No upstream PR was merged in this rehearsal.
