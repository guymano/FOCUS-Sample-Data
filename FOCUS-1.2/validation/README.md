# FOCUS 1.2 validation evidence

Reference environment: Python 3.12 / Windows, focus-validator 2.2.1, model 1.2.0.1,
`--applicability-criteria ALL --show-violations --block-download`. The model and
currency resource hashes are pinned in [runtime.json](runtime.json). These results
do not claim a Linux run or complete conformance.

[Current results](results.md) · [statistics](statistics.md) · [all expected rule states](expected.json)
· [failure explanations](failure-explanations.json) · [affected-record proofs](failure-examples.json)
· [upstream tracking](upstream-notes.md).

## Reproduce and record

```bash
python -m pip install -r FOCUS-1.2/validation/requirements.txt
python generators/validate_focus_1_2_samples.py
python generators/validate_focus_1_2_samples.py --check-existing
python generators/validate_focus_1_2_samples.py --record FOCUS-1.2/validation/local/candidate
python generators/reproduce_focus_1_2_validator.py --out FOCUS-1.2/validation/local/reproductions --run
```

If the installation lacks the model, obtain the [official versioned release asset](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/releases/download/v1.2/model-1.2.0.1.json)
and verify its runtime.json hash before installing it in focus_validator/rules.
The wrapper runs the unmodified package from its site-packages parent because 2.2.1
resolves currency_codes.csv relative to that directory. No validator source is patched.

Default/check-existing mode verifies data and generator hashes, model-resource hashes,
the complete rule inventory and states (PASS included), duplicate/missing rules,
totals and violation counts. It runs the independent data audit first. The official
executable can exit zero while rules fail; this wrapper examines the actual report.

--record writes a separate candidate directory: raw logs, per-file manifests, expected
states, independently counted failing populations, metrics and a results table. It
does not replace committed expectations. Review every changed population and any
new rule before promoting logs/manifests into after/, expected.json and failure-examples.json;
copy its summary.md to results.md and use the describe command to refresh statistics.
Existing explanations must still match the pinned model; an unknown failing population
stops recording. Rerun --check-existing, acceptance and regression tests after promotion.

before/ preserves the original pre-correction run. after/ records the current CSVs and
generator hashes; its base_revision identifies the preceding commit whose working
tree was modified. Earlier after/ snapshots remain available in Git history. Raw logs
are preserved byte-for-byte and treated as binary diffs to avoid CRLF normalization.

## Minimal reproductions

reproductions/ contains single-record synthetic CSV snippets, source record numbers,
hashes, targeted rule JSON, and full official logs. They isolate the named defects;
they are not complete billing periods or claims of whole-file conformance. The
reproduce command extracts them again from the current AWS sample and asserts the
target failures when --run is used.

## Failure counts by cause (including parent composites)

| Cause | AWS before/after | Azure before/after | GCP before/after |
|---|---:|---:|---:|
| Account ID type inference | 4/4 | 0/0 | 0/0 |
| CapacityReservationStatus | 3/3 | 3/3 | 3/3 |
| CommitmentDiscountStatus | 3/3 | 3/3 | 3/3 |
| CostAndUsage | 2/2 | 2/2 | 2/2 |
| EffectiveCost | 0/2 | 0/2 | 0/2 |
| InvoiceId | 1/1 | 1/1 | 1/1 |
| PricingCurrency | 2/0 | 2/0 | 2/0 |
| PricingCurrencyEffectiveCost | 2/0 | 2/0 | 2/0 |

The pricing-currency omissions in 1.2 were data defects and are fixed. The new
EffectiveCost failures follow the corrected period-subscription model: the rule
loses the future-covering condition. Residual nullability, JSON-condition and
account-typing artifacts are explained individually in the linked inventory.
Parent composite failures are counted once each, not described as extra bad rows.
Dynamic/unsupported checks remain skipped and are reported explicitly; independent
tests cover the fixture's arithmetic, SKU consistency, tax lineage and reconciliation.

## Local checks

[Acceptance](acceptance.log), [regressions](regressions.log), and [evidence check](evidence-check.log).
