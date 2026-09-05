# FOCUS 1.3 synthetic provider samples

AWS, Microsoft Azure and Google Cloud examples using the [FOCUS 1.3 specification](https://focus.finops.org/docs/specification/v1-3/).
Each Cost and Usage file has 1,000 rows and 65 columns.
These fixtures demonstrate selected scenarios; they are not a conformance certification.

## Generate and check

Python 3.11+ standard library; seeds, timestamps and UTF-8/LF CSV output are deterministic.
The local attributes preserve CSV and Python-source LF bytes on Windows.

```bash
python generators/generate_aws_focus_1_3.py --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_aws_1000.csv
python generators/generate_azure_focus_1_3.py --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_azure_1000.csv
python generators/generate_gcp_focus_1_3.py --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_costandusage_gcp_1000.csv

python generators/generate_aws_focus_1_3.py --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_aws.csv
python generators/generate_azure_focus_1_3.py --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_azure.csv
python generators/generate_gcp_focus_1_3.py --dataset contract_commitment --rows 1000 --seed 1302 --out FOCUS-1.3/focus_sample_contractcommitment_gcp.csv
python generators/check_focus_1_3_samples.py
python -m unittest discover -s generators -p 'test_focus_1_3_regressions.py'
python generators/describe_focus_1_3_samples.py --write
python generators/validate_focus_1_3_samples.py --check-existing
```

## Current data

<!-- BEGIN GENERATED STATISTICS -->
| Provider | Usage | Purchase | Tax | Discounts | Used | Unused |
|---|---:|---:|---:|---:|---:|---:|
| aws | 696 | 210 | 94 | 18 | 132 | 37 |
| azure | 675 | 228 | 97 | 19 | 133 | 38 |
| gcp | 680 | 224 | 96 | 20 | 134 | 35 |

| Provider | Billed = Effective cost (USD) | Commitment share | Utilization | Waste | Compute coverage |
|---|---:|---:|---:|---:|---:|
| aws | 33773.232522429145313 | 16.02% | 78.11% | 21.89% | 99.81% |
| azure | 70514.496245627744 | 15.53% | 77.78% | 22.22% | 99.82% |
| gcp | 43126.3717999335770 | 17.51% | 79.29% | 20.71% | 99.83% |

| Provider | Commitments | Non-discount terms | Contracts | Rows with ContractApplied |
|---|---:|---:|---:|---:|
| aws | 21 | 3 | 7 | 285 |
| azure | 22 | 3 | 8 | 300 |
| gcp | 23 | 3 | 8 | 296 |
<!-- END GENERATED STATISTICS -->

The committed files contain no Credit, marketplace or correction rows.
`--include-credits` adds optional negative credit scenarios. Capacity reservations
are not modeled; their identifiers and statuses remain null.

## Cost model, fleets and metrics

- Period subscription fees are recurring purchases consumed in their charge period:
  EffectiveCost equals BilledCost, with the corresponding pricing-currency amount.
- Each commitment covers 500 machine-equivalents per hourly period. Purchases cost
  USD 32.016 for AWS, 64.032 for Azure, or 44.689 for GCP. Every represented period
  has a purchase plus either fully Used or fully Unused usage. Unused allocation
  expires; it is not carried to a later period. Group utilization is partial across
  those periods. The example does not model partially used capacity within an hour.
- Used rows represent an aggregate Compute Fleet, with a stable synthetic
  `urn:focus-sample:...:compute-fleet:...` identity, owning SubAccountId and
  SyntheticFleetSize tag. 500 machine-hours describe the fleet, not one VM running
  500 hours in a one-hour period. Purchase/Unused rows identify the commitment.
- Purchase EffectiveCost is zero only for future-covering commitments; their costs
  reconcile exactly to Used plus Unused EffectiveCost per commitment and period.
- List, negotiated and effective commitment prices remain distinct. All applicable
  ListCost/ContractedCost products are exact Decimal arithmetic without a second rounding.
- Commitment share = commitment-purchase BilledCost / total BilledCost. The default
  fixture target is at least 5%, which is a pedagogical target, not a FOCUS rule.
- Utilization and waste divide Used and Unused EffectiveCost by commitment-purchase
  BilledCost. Coverage divides Used compute ListCost by all eligible compute Usage
  ListCost, excluding Unused, taxes, subscriptions and other services. These samples
  contain mostly covered fleet usage and a few individual public-price VMs, so
  coverage is near 100%; it is not a representative enterprise coverage benchmark.
- Every tax is 10% of one earlier Standard Usage record, at most once per source.
  ChargeDescription identifies its one-based data-record number, excluding the header.
  Identity, service, period and currency match the source; each cost derives from its
  corresponding source cost. The rate is synthetic, not jurisdiction-specific.
- Billing is USD; pricing may be EUR using the fixed illustrative conversion 0.92.
  Required currency values are present on taxes and optional credits.

The complete files and each account/period/currency bucket reconcile BilledCost and
EffectiveCost exactly. This is a closed-period fixture property, not a universal
FOCUS equality for arbitrary exports.

## SKU and resource identity

SkuId derives from provider, service, meter, region, unit and offer properties,
independent of seed, row, account and PricingCategory. Standard and Committed usage
share a consumption SKU. SkuPriceId adds list-price and currency information.
No row-level price jitter remains; subscription fees have a separate stable offer.
Storage uses FOCUS StorageClass/Redundancy keys: AWS Standard/Zonal, Azure Hot/Local,
GCP Standard. The `x_` prefix is reserved for custom properties.

AWS deliberately retains CUR-style ServiceName codes. Individual resource IDs use
explicit namespaces and SubAccountId ownership, including lambda/glue and allocated
workloads. They are synthetic ARN-style examples, not every service's exact native
grammar. Aggregate fleet URNs are explicitly synthetic and checked separately.

## Contract Commitment

The 13-column dataset includes three non-discount terms per provider: general
minimum spend, storage pricing, and compute hours. Several terms share one ContractId.
Join ContractApplied.Elements[].ContractCommitmentId to ContractCommitmentId and
verify its parent ContractId. A join on CommitmentDiscountId loses these terms.

An explicit service mapping applies the compute term only to EC2, Virtual Machines
or Compute Engine, and the storage term only to S3, Azure Blob Storage or Cloud
Storage. Other selected ordinary services use the general spend term. Approximately
35% of ordinary usage is selected deterministically; each selected row has one term.
Selected usage has a 10% negotiated discount (unit prices rounded to ten decimal
places, half up); ordinary usage with no contract, including split allocation, uses
the public price. Commitment-discount usage keeps its separate negotiated baseline.

Spend elements have ContractId, ContractCommitmentId and ContractCommitmentAppliedCost.
Usage elements additionally have ContractCommitmentAppliedQuantity and its string unit.
The keys follow erratum #3; the unit follows erratum #2. Inapplicable quantity/unit
properties are absent. Costs/quantities remain exact finite JSON numbers, including
split-allocation quantities; serialization never passes them through binary float.
Integral ContractCommitmentQuantity retains a decimal point in CSV.

The annual commitment describes 8,760 periods, not only those shown in the sample.
Its cost is the hourly fleet cost times 8,760; usage-based annual quantity is
4,380,000 machine-hours. Contract periods contain commitment periods, which contain
the charges they cover. Tests check service eligibility, units and these relationships.

## Validation and limitations

The acceptance and regression checks cover schemas, mandatory values, stable offers,
tax lineage, resource ownership, complete commitment groups, fleet size and costs,
and exact arithmetic. Tests include credits on/off, seeds 0/1/42/1302, row counts
1/2/11/12/23/24/25/1000/1001, forced budget boundaries and deliberate corruptions.
Small valid files need not contain every scenario. Statistics are recalculated from
the CSVs by the documented describe command; running it without --write checks them.

Official reference: focus-validator 2.2.1, model 1.3.0.1, applicability ALL.
See [validation evidence](validation/README.md) for raw reports, all rule states,
affected-record proofs and reproducible diagnostic snippets. Skipped rules are not
passes; residual artifacts are documented, not silently suppressed.

All three entry points use the local shared generation core, immutable provider
profiles and version adapters. Fleet sizing and the other reviewed corrections are
preserved; the refactoring reproduces the same CSV bytes. See
[non-regression evidence](validation/refactor/README.md).
