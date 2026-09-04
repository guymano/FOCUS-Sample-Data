# FOCUS 1.2 synthetic sample data

Provider-shaped synthetic examples for AWS, Microsoft Azure and Google Cloud,
using the [FOCUS 1.2 specification](https://focus.finops.org/docs/specification/v1-2/).
Cost and Usage has **57 columns and 1,000 rows per provider**.


These examples illustrate selected scenarios. The validator has documented
limitations; this is **not a claim of complete automated conformance certification**.

## Generate the files

Python 3.11+; the generators and acceptance/regression checks use only the standard
library. The seed, timestamps and UTF-8/LF serialization are deterministic.
The local `.gitattributes` preserves CSV LF bytes on Windows checkouts too.

```bash
python generators/generate_aws_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_aws_1000.csv
python generators/generate_azure_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_azure_1000.csv
python generators/generate_gcp_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_gcp_1000.csv
```

## What the files contain

| Provider | Usage | Purchase | Tax | Commitment discounts | Used | Unused |
|---|---:|---:|---:|---:|---:|---:|
| AWS | 687 | 232 | 81 | 20 | 144 | 37 |
| Microsoft Azure | 690 | 220 | 90 | 18 | 124 | 38 |
| Google Cloud | 695 | 217 | 88 | 18 | 118 | 36 |

The committed samples have no Credit, marketplace or correction rows.
`--include-credits` enables synthetic negative credits for additional testing.
Capacity reservation IDs/statuses remain null because that scenario is absent.

## Cost model and traceable taxes

- **Period subscription fees:** a standalone recurring Purchase is consumed in its
  own charge period. EffectiveCost equals BilledCost; PricingCurrencyEffectiveCost
  carries the corresponding amount. Its subscription offer has a stable synthetic
  fee per provider/service/region, distinct from the underlying consumption SKU.
- **Commitment discounts:** every represented hourly period has a recurring
  Purchase with EffectiveCost zero and one Usage row, either Used or Unused.
  Unused rows identify the commitment itself and have no ConsumedQuantity/Unit.
  Per commitment and billing period, usage EffectiveCost equals purchase BilledCost.
  Equality per charge period is an additional invariant of these fixtures.
- **Separate discounts:** list price, negotiated price and commitment-adjusted
  effective cost remain distinct. On Used rows, EffectiveCost < ContractedCost <= ListCost.
- **Exact arithmetic:** ListCost and ContractedCost equal unit price times quantity
  wherever unit pricing applies. Tax rows have no unit price/quantity and use the
  source-cost calculation below instead. Derived costs are not rounded again.
- **Synthetic taxes:** each tax is 10% of one earlier Standard Usage record, selected
  at most once. ChargeDescription gives the one-based data-record number (excluding
  the CSV header). Billing identity, service, charge period and pricing currency
  match that source; each cost uses its corresponding source cost. The 10% rate is
  pedagogical and does not model any jurisdiction. With no eligible source, the
  generator emits usage instead of an orphan tax.
- **Currency:** billing is USD; pricing can be USD or EUR, with the fixed synthetic
  conversion EUR = USD x 0.92. Taxes copy their source's pricing currency.

The following equality is a property of this closed-period synthetic model, not a
universal FOCUS requirement for arbitrary exports:

| Provider | Total BilledCost = total EffectiveCost (USD, exact) |
|---|---:|
| AWS | 35328.38867277753375 |
| Microsoft Azure | 70832.811318230304 |
| Google Cloud | 47524.7376918256860 |

## Stable offers and identifiers

SkuId derives from provider, service, meter, region, unit and SKU properties,
independent of row number, RNG seed, billing account and PricingCategory. The same
consumption offer has the same SKU for Standard and Committed usage. Subscription
and commitment-purchase offers have different meters/properties and remain distinct.
SkuPriceId adds list-price and currency information; no per-row price jitter remains.
IDs are synthetic SHA-256-derived labels, not actual provider catalog IDs.

Storage uses FOCUS `StorageClass` and `Redundancy` keys. The examples use AWS
Standard/Zonal, Azure Hot/Local, and GCP Standard. `x_` is reserved for custom keys.
The property-name checks are active rather than an unused list of constants.

AWS ServiceName intentionally retains CUR-style product codes. Resource IDs are
synthetic ARN-style illustrations, not a complete implementation of every service's
native ARN grammar. Namespaces are explicit (including lambda and glue); resource
ownership uses SubAccountId rather than the payer account, including committed usage.

## Acceptance and regression checks

```bash
python generators/check_focus_1_2_samples.py
python -m unittest discover -s generators -p 'test_focus_1_2_regressions.py'
python generators/validate_focus_1_2_samples.py --check-existing
```

The acceptance script checks the committed CSVs and byte-for-byte regeneration.
Independent data checks cover exact schemas, mandatory values, subscriptions,
source-linked taxes, stable SKU/price identities, resource ownership and complete
commitment pairs.

Regression tests exercise all three providers at sizes 1, 2, 11, 12, 23, 24, 25,
1000 and 1001, using seeds 0, 1, 42 and 1202, with credits enabled and disabled.
They force groups at and around their row budget, including a larger future group,
and reject deliberate corruptions of costs, tax sources, SKU IDs/prices, mandatory
values, AWS ownership and commitment pairs.
Small files need not contain every scenario. Tests require applicability, not
nonempty scenario sets that would make small valid files fail spuriously.

## Official validation status

The full before/after run uses **focus-validator 2.2.1**, model **1.2.0.1**,
and **--applicability-criteria ALL**. See [validation evidence](validation/README.md)
for exact versions, resource hashes, raw reports, per-rule explanations and commands.
Skipped rules are not passes. The wrapper checks actual rule results because the
official executable can exit zero even when rules fail.

| Dataset/provider | Failing rules before | Failing rules after | Skipped after |
|---|---:|---:|---:|
| costandusage_aws | 17 | 15 | 210 |
| costandusage_azure | 13 | 11 | 210 |
| costandusage_gcp | 13 | 11 | 210 |

The subscription correction exposes `EffectiveCost-C-005-C` (with a `CAU-` prefix
in 1.3) and its parent composite: the model checks every Purchase, omitting the
prose's condition that it covers future eligible charges. These two failures are
explained model artifacts, not a reason to erase period subscription costs.
The full failure inventory is linked above; no unknown failures are accepted.

Earlier results attributed to withdrawn version 2.2.0 are superseded by these
recorded 2.2.1 runs. Numbers quoted in earlier reviews describe their revisions,
not these regenerated files.

## Deliberate limitations and deferred work

Commitment amounts illustrate a small single-unit scenario; these files are not
representative fleet coverage/utilization benchmarks. Increasing that scale is
deferred. The three provider generators remain separate and self-contained;
extracting common code into a shared module is explicitly deferred.
