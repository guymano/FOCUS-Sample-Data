# Shared-core non-regression proof

Reference before extraction: `977f8184411ae332ee5d384ae34556281e0e3b10`. The adjacent
`../refactor-baseline.json` was captured by executing that commit's three original
generators before any extraction, not by regenerating expected hashes from the new
engine. It locks 216 outputs: sizes 1, 2, 11, 12, 23, 24, 25, 1000, 1001;
seeds 0, 1, 42 and the original default; optional credits on/off; and, for 1.3,
the corresponding Contract Commitment outputs. Published CSV hashes and previous
statistics/report/explanation hashes are recorded separately.

To independently reproduce the references, check out the recorded commit in a
separate clone and run its documented generator CLI for each case in the manifest
(`--rows`, `--seed`, `--include-credits`, and `--dataset contract_commitment` where
applicable), writing temporary outputs. SHA-256 each CSV and compare to the manifest.
Do not rewrite the baseline to accommodate a failing refactoring test.

`test_focus_shared.py` compares the new output to every frozen hash and checks that
the published CSV bytes are unchanged. JSON documentation hashes use Git's LF form
to allow Windows checkouts; CSV bytes are never normalized. The existing independent
semantic/negative tests remain intact. Tests additionally exercise a fake provider,
cross-provider/version state isolation, CLI/auditor loading and full source provenance.

Run `python generators/run_regression_checks.py --output-dir /path/to/check-results`
from the repository root. Python 3.11 and 3.12 on Windows and Linux are covered by the
recorded results. The 1.3 evidence includes both versions running on the same core.
The official-validator comparison is in `../refactor-validation-comparison.json`;
raw current reports are in `../after/`. No additional rule failures were accepted.

The toolkit supplied architectural inspiration only. Its code and data have not
been changed or imported as the semantic reference for this extraction.

## Preserved reference reports

`before/` contains the exact official reports, full expected rule inventory and
example populations from the frozen reference commit. Current reports remain in
`../after/`; `../refactor-validation-comparison.json` records the comparison.
Every rule state and violation count is unchanged, including passes and skips.

## Executed environments

- [Windows Python 3.11](windows311/result.json)
- [Windows Python 3.12](windows312/result.json)
- [Linux Python 3.11](linux311/result.json)
- [Linux Python 3.12](linux312/result.json)

Each result lists commands, exit codes and SHA-256 hashes of adjacent raw logs.
[Standalone FOCUS 1.2 checkout](standalone/result.json) also passes without any 1.3 extension installed.
