# FOCUS 1.2 sample data (provider-realistic, synthetic)

Synthetic, PII-free sample datasets conforming to
[FOCUS 1.2](https://focus.finops.org/focus-specification/v1-2/)
(Cost and Usage, 57 columns), with **provider-realistic values** for AWS,
Microsoft Azure and Google Cloud: real service names, SKUs, regions, pricing
units, commitment models (Savings Plans / Reservations / Committed Use
Discounts) and tax rows.

| File | Provider | Rows | Regenerate |
|------|----------|------|------------|
| `focus_sample_costandusage_aws_1000.csv` | AWS | 1000 | `python generators/generate_aws_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_aws_1000.csv` |
| `focus_sample_costandusage_azure_1000.csv` | Microsoft Azure | 1000 | `python generators/generate_azure_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_azure_1000.csv` |
| `focus_sample_costandusage_gcp_1000.csv` | Google Cloud | 1000 | `python generators/generate_gcp_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_gcp_1000.csv` |

Generation is deterministic (seeded RNG, fixed timestamps): the commands above
reproduce these files byte-for-byte. See `generators/README.md`.

## What the files contain

`Usage`, `Purchase` and `Tax` rows. **No `Credit` rows**: the generators can emit them
behind `--include-credits`, but the committed fixtures do not use it. No marketplace
rows either — `PublisherName` and `InvoiceIssuerName` hold a single value per provider.
`ChargeClass` is never populated (nothing here is a correction), and
`CapacityReservationId` / `CapacityReservationStatus` are always null, which the spec
requires for charges unrelated to a capacity reservation.

| Provider | Commitment discounts | Rows tied to a commitment | `Used` | `Unused` |
|---|---|---|---|---|
| AWS | 16 | 264 | 106 | 26 |
| Microsoft Azure | 19 | 340 | 133 | 37 |
| Google Cloud | 21 | 378 | 148 | 41 |

## Commitment discounts are modelled per charge period

FOCUS amortises a commitment discount evenly over each charge period of its term,
use-it-or-lose-it: what a period does not consume is wasted rather than carried
forward. Each commitment here therefore carries, for every hourly charge period the
fixture holds, a recurring purchase row (`ChargeCategory = Purchase`,
`ChargeFrequency = Recurring`, `PricingCategory = Standard`, the commitment's id in both
`ResourceId` and `CommitmentDiscountId`) and one usage row — either
`CommitmentDiscountStatus = "Used"`, naming the resource that drew the commitment down,
or `"Unused"`, priced against the commitment itself with `ConsumedQuantity` and
`ConsumedUnit` null. Per charge period and over the whole commitment,
`sum(EffectiveCost where Usage) == sum(BilledCost where Purchase)`.

A spend-based commitment is drawn down in currency and a usage-based one in the
commitment's own unit, so `CommitmentDiscountQuantity`, `PricingQuantity` and
`PricingUnit` branch on `CommitmentDiscountCategory`: USD for `Spend`, hours for `Usage`.

**Three prices, kept apart.** `ContractedUnitPrice` is defined as inclusive of
negotiated discounts but *excluding* commitment discounts, so a committed usage row
carries the negotiated price there and shows the commitment's saving only in
`EffectiveCost`:

```
ListCost        list price           -- what it would have cost at rate card
ContractedCost  negotiated price     -- the negotiation saving is List - Contracted
EffectiveCost   amortised commitment -- the commitment saving is Contracted - Effective
```

**Exact cost arithmetic.** FOCUS requires the product of `ListUnitPrice` and
`PricingQuantity` to match `ListCost`, and likewise for `ContractedCost`, with no
rounding tolerance outside corrections. Unit prices keep their full ten decimals — some
are genuinely that small — and derived costs are the exact product rather than a
six-decimal rounding of it, so they carry as many decimals as the multiplication
produces, trailing zeros trimmed.

## Checks

```bash
python generators/check_focus_1_2_samples.py
```

Twenty-four assertions per provider against the committed CSVs: byte reproducibility,
the 57 columns, the exact cost arithmetic, commitment reconciliation (per
`CommitmentDiscountId`, which is the normative requirement, and again per charge period,
which is an additional invariant of these fixtures), the shape of purchase / `Used` /
`Unused` rows, the price ordering `EffectiveCost < ContractedCost <= ListCost`,
conditional nullability of `PricingQuantity` / `PricingUnit` / `Consumed*`, and
billing-identity consistency — one `BillingAccountName` and one `InvoiceId` per
`BillingAccountId`, and a single identity across every row of a commitment group.

## Validation status

Earlier revisions of this README reported 136 passing rules with one or two residual
artifacts. Those figures are withdrawn: they came from a run whose validator release has
since been retracted, and they are contradicted by the requirements this revision fixes —
the cost products, the commitment reconciliation, the contracted price, and the billing
identity, each of which failed on hundreds of rows.

**On the validator version.** The run used `focus_validator` **2.2.0**, published to
PyPI on 2026-06-25 and since **yanked** by its maintainer as premature — the yank reason
reads "pre-mature release. Will need to proceed to a 2.2.1 with the correct release" —
and it never carried a git tag, which is why it does not appear in the project's version
list. The number is left as-is rather than silently rewritten to 2.2.1, which would claim
a run that did not happen. **The `1.2.0.1` run should be re-established on 2.2.1** before
any conformance claim is made here.

**One artifact is expected to survive that run**: `InvoiceId-C-004-C` ("InvoiceId MUST be
null") fires on every non-null `InvoiceId`. It is one branch of the composite
`InvoiceId-C-003-C`, defined in the rule model as `OR(C-004-C, C-005-C)` where `C-004-C`
requires the value to be null and `C-005-C` requires it not to be — the two branches
exclude each other by construction, so exactly one of them fails on every row and only
the composite is meaningful. Any dataset with populated invoice ids reports it.

On AWS, a CSV reader that infers column types will also turn `BillingAccountId` **and**
`SubAccountId` into numbers: both are 12-digit numeric strings there. Azure (GUIDs) and
Google Cloud (billing-account and project ids) are unaffected. Any real AWS FOCUS CSV
export exhibits the same artifact.
