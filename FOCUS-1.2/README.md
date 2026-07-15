# FOCUS 1.2 sample data (provider-realistic, synthetic)

Synthetic, PII-free sample datasets conforming to
[FOCUS 1.2](https://focus.finops.org/focus-specification/v1-2/)
(Cost and Usage, 57 columns), with **provider-realistic values** for AWS,
Microsoft Azure and Google Cloud: real service names, SKUs, regions, pricing
units, commitment models (Savings Plans / Reservations / Committed Use
Discounts), tax and credit rows.

| File | Provider | Rows | Regenerate |
|------|----------|------|------------|
| `focus_sample_costandusage_aws_1000.csv` | AWS | 1000 | `python generators/generate_aws_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_aws_1000.csv` |
| `focus_sample_costandusage_azure_1000.csv` | Microsoft Azure | 1000 | `python generators/generate_azure_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_azure_1000.csv` |
| `focus_sample_costandusage_gcp_1000.csv` | Google Cloud | 1000 | `python generators/generate_gcp_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_gcp_1000.csv` |

Generation is deterministic (seeded RNG, fixed timestamps): the commands above
reproduce these files byte-for-byte. See `generators/README.md`.

## Validation status

Validated with the official
[focus_validator](https://github.com/finopsfoundation/focus_validator) v2.2.0
against rule model `1.2.0.1`
(`focus-validator --data-file <file> --validate-version 1.2.0.1`):

- **Azure**: 136 rules pass, 1 residual failure (see below).
- **GCP**: 136 rules pass, 1 residual failure (see below).
- **AWS**: 134 rules pass, 2 residual failures (see below).

Residual failures are validator-side artifacts, not data errors:

1. `InvoiceId-C-004-C` ("InvoiceId MUST be NULL") fires on every non-null
   `InvoiceId`. It is one branch of an OR pair (`C-004-C` null / `C-005-C`
   not-null) whose parent rule passes; the standalone child failure is a known,
   already-triaged reporting artifact of the contradictory InvoiceId null
   rules. Any dataset with populated invoice ids reports it.
2. AWS only: `BillingAccountId-C-002-M` ("MUST be of type String"). AWS billing
   account ids are 12-digit strings (e.g. `100000000001`); CSV carries no type
   information and the validator's loader infers a numeric column. Any real
   AWS FOCUS CSV export exhibits the same artifact.
