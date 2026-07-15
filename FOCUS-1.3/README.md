# FOCUS 1.3 sample data (provider-realistic, synthetic)

Synthetic, PII-free sample datasets conforming to
[FOCUS 1.3](https://focus.finops.org/focus-specification/v1-3/), with
**provider-realistic values** for AWS, Microsoft Azure and Google Cloud.
FOCUS 1.3 defines two datasets, both provided here:

- **Cost and Usage** (65 columns): 1.2's 57 columns plus the 1.3 provider
  split (`ServiceProviderName`/`HostProviderName`, with the deprecated
  `ProviderName`/`PublisherName` retained), the Split Cost Allocation columns
  and `ContractApplied`.
- **Contract Commitment** (13 columns): every row joins to Cost and Usage via
  `ContractCommitmentId == CommitmentDiscountId` (join verified: 73–75
  commitments per provider, all matched).

| File | Provider | Dataset | Regenerate |
|------|----------|---------|------------|
| `focus_sample_costandusage_aws_1000.csv` | AWS | Cost and Usage (1000 rows) | `python generators/generate_aws_focus_1_3.py --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_aws_1000.csv` |
| `focus_sample_costandusage_azure_1000.csv` | Microsoft Azure | Cost and Usage (1000 rows) | `python generators/generate_azure_focus_1_3.py --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_azure_1000.csv` |
| `focus_sample_costandusage_gcp_1000.csv` | Google Cloud | Cost and Usage (1000 rows) | `python generators/generate_gcp_focus_1_3.py --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_gcp_1000.csv` |
| `focus_sample_contractcommitment_aws.csv` | AWS | Contract Commitment | `python generators/generate_aws_focus_1_3.py --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_aws.csv` |
| `focus_sample_contractcommitment_azure.csv` | Microsoft Azure | Contract Commitment | `python generators/generate_azure_focus_1_3.py --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_azure.csv` |
| `focus_sample_contractcommitment_gcp.csv` | Google Cloud | Contract Commitment | `python generators/generate_gcp_focus_1_3.py --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_gcp.csv` |

Generation is deterministic (seeded RNG, fixed timestamps): the commands above
reproduce these files byte-for-byte. See `generators/README.md`.

## Validation status

The 57 columns shared with FOCUS 1.2 were validated with the official
[focus_validator](https://github.com/finopsfoundation/focus_validator) v2.2.0
against rule model `1.2.0.1`, with the same results as the `FOCUS-1.2/`
samples: Azure and GCP pass all applicable rules except the known
`InvoiceId-C-004-C` reporting artifact; AWS additionally reports the
`BillingAccountId` CSV numeric-type-inference artifact (12-digit account ids).
See `FOCUS-1.2/README.md` for details on both.

Full 1.3 validation (including the 1.3-only columns and the Contract
Commitment dataset) uses the `1.3.0.1` rule model shipped with the FOCUS_Spec
v1.3 release:

```bash
focus-validator --data-file FOCUS-1.3/focus_sample_costandusage_aws_1000.csv --validate-version 1.3.0.1
```
