# FOCUS 1.2 validation evidence

Measured against the pre-correction branch revision and the regenerated CSVs.
Every per-file JSON manifest records the input SHA-256, base revision, command,
model/currency-resource hashes, individual failures and skipped rules. The after
manifests also identify the generator source by SHA-256. Console logs are retained
unaltered; timing values are informational and need not repeat.

- [Runtime and rule hashes](runtime.json)
- [Exact validation-environment packages](requirements.txt)
- [Before/after counts](summary.json)
- [Every residual failure and its actual model rule](failure-explanations.json)
- [Reviewed after expectations](expected.json)
- [Affected-row examples and measured counts](failure-examples.json)
- [Prepared upstream findings and existing tickets](upstream-notes.md)

## Reproduce

Use Python 3.12 in an isolated environment. Install the recorded requirements;
the generators themselves do not require these packages. `uv pip install` was
used successfully, including the pandasql build, with a writable local cache.
The recorded runtime is Windows; test results below do not claim a Linux run.

```bash
python -m pip install -r FOCUS-1.2/validation/requirements.txt
python generators/validate_focus_1_2_samples.py
```

The wrapper invokes the unmodified validator from its installed package's parent
directory because 2.2.1 resolves `focus_validator/rules/currency_codes.csv` against
the working directory. It supplies absolute data paths and always uses
`--validate-version 1.2.0.1 --applicability-criteria ALL --show-violations`.
It blocks remote rule replacement and verifies the recorded model/resource hashes.
If a fresh installation lacks model-1.2.0.1.json, obtain [the official v1.2 model](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/releases/download/v1.2/model-1.2.0.1.json)
from FOCUS_Spec and verify its runtime.json hash before running the wrapper.

`--check-existing` checks saved reports and input hashes without installing the
validator. Live output goes to ignored `validation/local/`, leaving evidence intact.
Both modes run the independent CSV audit first. Changed inputs, incomplete reports,
unreviewed failing rules/counts or changed skipped-rule sets result in a nonzero exit.
This gate confirms the reviewed evidence; it does not turn artifacts into passes.

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

[Acceptance output](acceptance.log), [regression output](regressions.log), and
[saved-evidence check](evidence-check.log) are recorded alongside the official reports.
