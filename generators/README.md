# FOCUS sample-data generators (provider-realistic, deterministic)

Deterministic Python generators that produce **provider-realistic** synthetic
FOCUS datasets for **AWS, Azure and GCP**, in **FOCUS 1.2** and **FOCUS 1.3**.

They complement the model-driven generation tooling (see PR #5 / `focusgen`):
where model-driven generation targets the validator's rule set with generic
values, these generators emit data that *looks like the provider* — realistic
services, SKUs, regions, instance types, pricing units, commitment models
(Savings Plans / Reservations / CUDs), tax, credit and marketplace-style rows —
while conforming to the FOCUS column set and conditionality rules.

## Properties

- **Deterministic**: seeded RNG + fixed timestamps. A given `(rows, seed)` pair
  is byte-reproducible, so committed samples can be regenerated and diffed.
- **Synthetic / PII-free**: no real account data; account ids, resource ids and
  names are generated.
- **Self-contained**: Python 3.11+ standard library only. No dependencies.
- **Normalized across providers**: identical column sets per FOCUS version, as
  the spec requires; only the values differ per provider.

## Usage

```bash
# FOCUS 1.2 — Cost and Usage (57 columns)
python generators/generate_aws_focus_1_2.py   --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_aws_1000.csv
python generators/generate_azure_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_azure_1000.csv
python generators/generate_gcp_focus_1_2.py   --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_gcp_1000.csv

# FOCUS 1.3 — Cost and Usage (65 columns)
python generators/generate_aws_focus_1_3.py   --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_aws_1000.csv
python generators/generate_azure_focus_1_3.py --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_azure_1000.csv
python generators/generate_gcp_focus_1_3.py   --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_gcp_1000.csv

# FOCUS 1.3 — Contract Commitment (13 columns, joinable to Cost and Usage
# via ContractCommitmentId == CommitmentDiscountId)
python generators/generate_aws_focus_1_3.py   --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_aws.csv
python generators/generate_azure_focus_1_3.py --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_azure.csv
python generators/generate_gcp_focus_1_3.py   --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_gcp.csv
```

## Validation

Generated samples were run through the official
[focus_validator](https://github.com/finopsfoundation/focus_validator)
(v2.2.0). See `FOCUS-1.2/README.md` and `FOCUS-1.3/README.md` for per-file
results and the two known validator-side artifacts that remain (rule
`InvoiceId-C-004-C`, and CSV numeric-type inference on AWS's 12-digit
`BillingAccountId`).

## License

Contributed under the repository license (CC BY 4.0).
