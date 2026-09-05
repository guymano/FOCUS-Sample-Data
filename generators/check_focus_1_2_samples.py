"""Acceptance checks for the committed FOCUS 1.2 samples.

Run from the repository root:

    python generators/check_focus_1_2_samples.py

Every check is a normative FOCUS 1.2 requirement or an invariant the samples claim
in ``FOCUS-1.2/README.md``. Exits non-zero if any check fails, so it can be wired
into CI.
"""

from __future__ import annotations

import csv
import re
import importlib.util
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS = ("aws", "azure", "gcp")
COLUMNS = 57

BILLING_IDENTITY = (
    "BillingAccountId",
    "BillingAccountName",
    "BillingAccountType",
    "SubAccountId",
    "SubAccountName",
    "SubAccountType",
    "InvoiceId",
)


def _load(provider: str):
    path = ROOT / "generators" / f"generate_{provider}_focus_1_2.py"
    spec = importlib.util.spec_from_file_location(f"gen12_{provider}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _dec(value: str) -> Decimal:
    return Decimal(value)


class Checker:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        if ok:
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label}{': ' + detail if detail else ''}")
            self.failures.append(label)


EXPECTED_COLUMNS = ('ProviderName',
 'PublisherName',
 'InvoiceIssuerName',
 'InvoiceId',
 'BillingAccountId',
 'BillingAccountName',
 'BillingAccountType',
 'SubAccountId',
 'SubAccountName',
 'SubAccountType',
 'BillingPeriodStart',
 'BillingPeriodEnd',
 'ChargePeriodStart',
 'ChargePeriodEnd',
 'ChargeCategory',
 'ChargeClass',
 'ChargeDescription',
 'ChargeFrequency',
 'BilledCost',
 'EffectiveCost',
 'ListCost',
 'ContractedCost',
 'ListUnitPrice',
 'ContractedUnitPrice',
 'PricingCategory',
 'PricingQuantity',
 'PricingUnit',
 'PricingCurrency',
 'PricingCurrencyContractedUnitPrice',
 'PricingCurrencyEffectiveCost',
 'PricingCurrencyListUnitPrice',
 'BillingCurrency',
 'ConsumedQuantity',
 'ConsumedUnit',
 'ServiceName',
 'ServiceCategory',
 'ServiceSubcategory',
 'SkuId',
 'SkuMeter',
 'SkuPriceId',
 'SkuPriceDetails',
 'ResourceId',
 'ResourceName',
 'ResourceType',
 'RegionId',
 'RegionName',
 'AvailabilityZone',
 'CommitmentDiscountId',
 'CommitmentDiscountName',
 'CommitmentDiscountCategory',
 'CommitmentDiscountType',
 'CommitmentDiscountStatus',
 'CommitmentDiscountQuantity',
 'CommitmentDiscountUnit',
 'CapacityReservationId',
 'CapacityReservationStatus',
 'Tags')

# These checks read the exported data, independently of the generator helpers.
NEVER_NULL = (
    "ProviderName", "PublisherName", "InvoiceIssuerName", "BilledCost", "EffectiveCost",
    "ListCost", "ContractedCost", "BillingAccountId", "BillingPeriodStart", "BillingPeriodEnd",
    "ChargePeriodStart", "ChargePeriodEnd", "ChargeCategory", "ChargeFrequency", "BillingCurrency",
    "PricingCurrency", "PricingCurrencyEffectiveCost", "ServiceName", "ServiceCategory", "ServiceSubcategory",
)
SKU_PROPERTIES = {
    "StorageClass", "Redundancy", "CoreCount", "MemorySize", "InstanceType", "InstanceSeries",
    "OperatingSystem", "DiskType", "DiskSpace", "DiskMaxIops", "GpuCount", "NetworkMaxIops",
    "NetworkMaxThroughput",
}
COSTS = ("BilledCost", "EffectiveCost", "ListCost", "ContractedCost", "PricingCurrencyEffectiveCost")
AWS_NAMESPACES = {
    "AmazonEC2": "ec2", "AmazonS3": "s3", "AmazonRDS": "rds", "AWSLambda": "lambda",
    "AmazonVPC": "ec2", "AmazonCloudWatch": "cloudwatch", "AmazonDynamoDB": "dynamodb", "AWSGlue": "glue",
}


def sku_errors(rows: list[dict[str, str]]) -> list[str]:
    errors = []
    offers, ids, prices, price_ids = {}, {}, {}, {}
    for number, row in enumerate(rows, 1):
        if row["ChargeCategory"] not in ("Usage", "Purchase"):
            continue
        try:
            details = json.loads(row["SkuPriceDetails"])
            if not isinstance(details, dict):
                raise ValueError("SKU properties must be an object")
            if any((key.startswith("x_") and key[2:] in SKU_PROPERTIES)
                   or (not key.startswith("x_") and key not in SKU_PROPERTIES) for key in details):
                errors.append(f"sku: record {number} misnames a SKU property")
            offer = (row["ProviderName"], row["ServiceName"], row["RegionId"], row["SkuMeter"],
                     row["PricingUnit"], json.dumps(details, sort_keys=True))
            price = (row["SkuId"], row["BillingCurrency"], row["PricingCurrency"],
                     Decimal(row["ListUnitPrice"]), Decimal(row["PricingCurrencyListUnitPrice"]))
            for mapping, key, value in (
                (offers, offer, row["SkuId"]), (ids, row["SkuId"], offer),
                (prices, price, row["SkuPriceId"]), (price_ids, row["SkuPriceId"], price),
            ):
                if not row["SkuId"] or not row["SkuPriceId"] or mapping.setdefault(key, value) != value:
                    errors.append(f"sku: record {number} has an unstable or conflicting SKU/price identity")
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            errors.append(f"sku: record {number}: {exc}")
    return errors



COMPUTE_SERVICE = {"aws": "AmazonEC2", "azure": "Virtual Machines", "gcp": "Compute Engine"}
STORAGE_SERVICE = {"aws": "AmazonS3", "azure": "Azure Blob Storage", "gcp": "Cloud Storage"}
HOURLY_COMMITMENT = {"aws": Decimal("32.016"), "azure": Decimal("64.032"), "gcp": Decimal("44.689")}


def fixture_metrics(rows, provider):
    """Ratios use only their stated populations; taxes/subscriptions never count as coverage."""
    total = sum((Decimal(r["BilledCost"]) for r in rows), Decimal(0))
    purchase = sum((Decimal(r["BilledCost"]) for r in rows
                    if r["ChargeCategory"] == "Purchase" and r["CommitmentDiscountId"]), Decimal(0))
    used = sum((Decimal(r["EffectiveCost"]) for r in rows if r["CommitmentDiscountStatus"] == "Used"), Decimal(0))
    unused = sum((Decimal(r["EffectiveCost"]) for r in rows if r["CommitmentDiscountStatus"] == "Unused"), Decimal(0))
    eligible = [r for r in rows if r["ChargeCategory"] == "Usage"
                and r["ServiceName"] == COMPUTE_SERVICE[provider]
                and r["CommitmentDiscountStatus"] != "Unused" and r["PricingUnit"] == "Hours"]
    covered = sum((Decimal(r["ListCost"]) for r in eligible if r["CommitmentDiscountStatus"] == "Used"), Decimal(0))
    eligible_cost = sum((Decimal(r["ListCost"]) for r in eligible), Decimal(0))
    ratio = lambda a, b: str(a / b) if b else None
    return {"billed_cost": str(total), "commitment_purchases": str(purchase),
            "used_effective_cost": str(used), "unused_effective_cost": str(unused),
            "eligible_list_cost": str(eligible_cost), "covered_list_cost": str(covered),
            "commitment_share": ratio(purchase, total), "utilization": ratio(used, purchase),
            "waste": ratio(unused, purchase), "coverage": ratio(covered, eligible_cost)}


def fleet_errors(rows, provider):
    errors, identifiers = [], {}
    for number, row in enumerate(rows, 1):
        if not row["CommitmentDiscountId"]:
            continue
        if row["ChargeCategory"] == "Purchase" and Decimal(row["BilledCost"]) != HOURLY_COMMITMENT[provider]:
            errors.append(f"commitment: record {number} does not purchase the 500-unit hourly fleet")
        quantity = HOURLY_COMMITMENT[provider] if row["CommitmentDiscountCategory"] == "Spend" else Decimal(500)
        if Decimal(row["CommitmentDiscountQuantity"]) != quantity:
            errors.append(f"commitment: record {number} has the wrong fleet drawdown")
        if row["CommitmentDiscountStatus"] == "Used":
            prefix = f"urn:focus-sample:{provider}:{row['RegionId']}:{row['SubAccountId']}:compute-fleet:"
            if (not row["ResourceId"].startswith(prefix) or row["ResourceType"] != "Compute Fleet"
                or json.loads(row["Tags"]).get("SyntheticFleetSize") != "500"
                or identifiers.setdefault(row["CommitmentDiscountId"], row["ResourceId"]) != row["ResourceId"]):
                errors.append(f"resource: record {number} has an invalid or unstable fleet identity")
            if (Decimal(row["ConsumedQuantity"]) != 500 or Decimal(row["PricingQuantity"]) != 500
                or row["ConsumedUnit"] != "Hours" or row["PricingUnit"] != "Hours"
                or Decimal(row["EffectiveCost"]) != HOURLY_COMMITMENT[provider]):
                errors.append(f"commitment: record {number} has the wrong fleet consumption")
    return errors


def audit_rows(rows: list[dict[str, str]], provider: str) -> list[str]:
    """Fixture invariants for arbitrary sizes/seeds; no scenario-presence assumption."""
    errors = []
    periods = defaultdict(list)
    balances = defaultdict(Decimal)
    taxed_sources = set()
    for number, row in enumerate(rows, 1):
        if tuple(row) != EXPECTED_COLUMNS:
            errors.append(f"required: record {number} has the wrong column names/order")
            continue
        for name in NEVER_NULL:
            if not row[name]:
                errors.append(f"required: record {number} has empty {name}")
        try:
            if any(not Decimal(row[name]).is_finite() for name in COSTS):
                errors.append(f"cost: record {number} has a non-finite cost")
                continue
            category = row["ChargeCategory"]
            if category in ("Usage", "Purchase"):
                for cost, price in (("ListCost", "ListUnitPrice"), ("ContractedCost", "ContractedUnitPrice")):
                    if Decimal(row[cost]) != Decimal(row[price]) * Decimal(row["PricingQuantity"]):
                        errors.append(f"cost: record {number} has incorrect {cost}")
            if category == "Purchase" and not row["CommitmentDiscountId"]:
                if Decimal(row["EffectiveCost"]) != Decimal(row["BilledCost"]):
                    errors.append(f"cost: record {number} loses its period subscription cost")
            if category == "Credit" and not all(Decimal(row[name]) < 0 for name in COSTS):
                errors.append(f"cost: record {number} has an invalid credit sign")
            fx = {"USD": Decimal(1), "EUR": Decimal("0.92")}[row["PricingCurrency"]]
            if Decimal(row["PricingCurrencyEffectiveCost"]) != Decimal(row["EffectiveCost"]) * fx:
                errors.append(f"cost: record {number} has incorrect pricing-currency effective cost")
            balance_key = tuple(row[name] for name in (
                "BillingAccountId", "SubAccountId", "BillingPeriodStart", "BillingPeriodEnd", "BillingCurrency"))
            balances[balance_key] += Decimal(row["BilledCost"]) - Decimal(row["EffectiveCost"])
            if row["CommitmentDiscountId"]:
                key = tuple(row[name] for name in ("CommitmentDiscountId", "ChargePeriodStart", "ChargePeriodEnd"))
                periods[key].append(row)
            if category == "Tax":
                match = re.fullmatch(r"Synthetic tax 10% on usage record (\d+): (.+)", row["ChargeDescription"])
                if not match:
                    raise ValueError("tax source reference missing")
                source_number = int(match[1])
                if not 1 <= source_number < number or source_number in taxed_sources:
                    raise ValueError("invalid or duplicate tax source")
                taxed_sources.add(source_number)
                source = rows[source_number - 1]
                if source["ChargeCategory"] != "Usage" or source["PricingCategory"] != "Standard":
                    raise ValueError("tax source must be standard usage")
                identity = (*BILLING_IDENTITY, "BillingPeriodStart", "BillingPeriodEnd", "ServiceName",
                            "ChargePeriodStart", "ChargePeriodEnd", "BillingCurrency", "PricingCurrency")
                if any(row[name] != source[name] for name in identity) or match[2] != source["ServiceName"]:
                    errors.append(f"tax: record {number} has the wrong source identity")
                if any(Decimal(row[name]) != Decimal(source[name]) * Decimal("0.1") for name in COSTS):
                    errors.append(f"tax: record {number} is not 10% of its source costs")
                if any(row[name] for name in ("PricingCategory", "SkuId", "SkuPriceId", "ResourceId",
                       "ResourceType", "PricingQuantity", "PricingUnit", "ListUnitPrice", "ContractedUnitPrice",
                       "PricingCurrencyListUnitPrice", "PricingCurrencyContractedUnitPrice")):
                    errors.append(f"tax: record {number} populates inapplicable fields")
            if provider == "aws" and row["ResourceId"] and row["ResourceId"] != row["CommitmentDiscountId"] and row["ResourceType"] != "Compute Fleet":
                arn = row["ResourceId"].split(":", 5)
                if len(arn) != 6 or arn[2] != AWS_NAMESPACES[row["ServiceName"]] or arn[4] != row["SubAccountId"]:
                    errors.append(f"resource: record {number} has the wrong AWS namespace/owner")
        except (ValueError, TypeError, KeyError, ArithmeticError, IndexError) as exc:
            label = "tax" if row["ChargeCategory"] == "Tax" else "cost"
            errors.append(f"{label}: record {number}: {exc}")
    for key, group in periods.items():
        purchases = [r for r in group if r["ChargeCategory"] == "Purchase"]
        usage = [r for r in group if r["ChargeCategory"] == "Usage"]
        if len(purchases) != 1 or len(usage) != 1:
            errors.append(f"commitment: {key} is not a complete purchase/usage pair")
        elif (Decimal(purchases[0]["BilledCost"]) != Decimal(usage[0]["EffectiveCost"])
              or Decimal(purchases[0]["EffectiveCost"]) != 0 or Decimal(usage[0]["BilledCost"]) != 0):
            errors.append(f"commitment: {key} does not reconcile exactly")
    if any(balances.values()):
        errors.append("cost: billed and effective totals do not reconcile per account/period/currency [fixture invariant]")
    errors.extend(sku_errors(rows))
    errors.extend(fleet_errors(rows, provider))
    return errors


def check_provider(provider: str, checker: Checker) -> None:
    print(f"\n{provider.upper()}")
    module = _load(provider)
    path = ROOT / "FOCUS-1.2" / f"focus_sample_costandusage_{provider}_1000.csv"
    rows = _rows(path)

    failures = audit_rows(rows, provider)
    for category in ("required", "cost", "tax", "sku", "resource", "commitment"):
        found = [error for error in failures if error.startswith(category + ":")]
        checker.check(not found, f"independent {category} invariants", "; ".join(found[:5]))

    metrics = fixture_metrics(rows, provider)
    checker.check(Decimal(metrics["commitment_share"]) >= Decimal("0.05"),
                  "default fleet commitments represent at least 5% of billed cost [fixture target]")
    checker.check(all(Decimal(0) <= Decimal(metrics[k]) <= 1 for k in ("utilization", "waste", "coverage")),
                  "fleet utilization, waste and eligible-compute coverage are bounded")

    checker.check(
        module.generate_csv_bytes(1000, 1202) == path.read_bytes(),
        "the committed file is byte-reproducible",
    )
    checker.check(len(rows[0]) == COLUMNS, "57 columns", f"got {len(rows[0])}")

    # Cost arithmetic: exact, no rounding tolerance outside corrections.
    for cost_col, price_col in (
        ("ListCost", "ListUnitPrice"),
        ("ContractedCost", "ContractedUnitPrice"),
    ):
        bad = [
            row
            for row in rows
            if row[price_col] and row["PricingQuantity"]
            and _dec(row[cost_col]) != _dec(row[price_col]) * _dec(row["PricingQuantity"])
        ]
        checker.check(
            not bad,
            f"{cost_col} == {price_col} x PricingQuantity where unit pricing applies",
            f"{len(bad)} rows differ",
        )

    # Commitment reconciliation. Per CommitmentDiscountId is the normative requirement;
    # per charge period is an additional invariant these fixtures hold to.
    def _reconcile(key_fields, label: str) -> None:
        purchases: dict[tuple, Decimal] = defaultdict(Decimal)
        usage: dict[tuple, Decimal] = defaultdict(Decimal)
        for row in rows:
            if not row["CommitmentDiscountId"]:
                continue
            key = tuple(row[field] for field in key_fields)
            if row["ChargeCategory"] == "Purchase":
                purchases[key] += _dec(row["BilledCost"])
            elif row["ChargeCategory"] == "Usage":
                usage[key] += _dec(row["EffectiveCost"])
        keys = set(purchases) | set(usage)
        bad = [key for key in keys if purchases[key] != usage[key]]
        checker.check(not bad, label, f"{len(bad)} of {len(keys)} groups unbalanced")

    _reconcile(
        ("CommitmentDiscountId", "BillingPeriodStart", "BillingPeriodEnd"),
        "sum(Usage EffectiveCost) == sum(Purchase BilledCost) per commitment [normative]",
    )
    _reconcile(
        ("CommitmentDiscountId", "ChargePeriodStart", "ChargePeriodEnd"),
        "the same holds per charge period [fixture invariant]",
    )

    by_status: dict[str, Decimal] = defaultdict(Decimal)
    usage_total = Decimal(0)
    for row in rows:
        if row["CommitmentDiscountId"] and row["ChargeCategory"] == "Usage":
            usage_total += _dec(row["EffectiveCost"])
            by_status[row["CommitmentDiscountStatus"]] += _dec(row["EffectiveCost"])
    checker.check(
        usage_total == by_status["Used"] + by_status["Unused"]
        and set(by_status) == {"Used", "Unused"},
        "usage EffectiveCost splits into Used + Unused, and nothing else",
        f"statuses seen: {sorted(by_status)}",
    )

    # Commitment purchase rows.
    purchase_rows = [
        row for row in rows
        if row["ChargeCategory"] == "Purchase" and row["CommitmentDiscountId"]
    ]
    checker.check(bool(purchase_rows), "the dataset contains commitment purchase rows")
    checker.check(
        all(
            row["ChargeFrequency"] == "Recurring"
            and row["PricingCategory"] == "Standard"
            and row["ResourceId"] == row["CommitmentDiscountId"]
            and _dec(row["EffectiveCost"]) == 0
            for row in purchase_rows
        ),
        "commitment purchases: Recurring, Standard, ResourceId is the commitment, EffectiveCost 0",
    )

    # Used and Unused rows.
    unused_rows = [row for row in rows if row["CommitmentDiscountStatus"] == "Unused"]
    used_rows = [row for row in rows if row["CommitmentDiscountStatus"] == "Used"]
    checker.check(bool(unused_rows), "the dataset exercises CommitmentDiscountStatus Unused")
    checker.check(
        all(
            row["ChargeCategory"] == "Usage"
            and row["ChargeFrequency"] == "Usage-Based"
            and row["PricingCategory"] == "Committed"
            and row["ResourceId"] == row["CommitmentDiscountId"]
            and _dec(row["BilledCost"]) == 0
            for row in unused_rows
        ),
        "Unused rows: Usage / Usage-Based / Committed, ResourceId is the commitment, BilledCost 0",
    )
    checker.check(
        all(not row["ConsumedQuantity"] and not row["ConsumedUnit"] for row in unused_rows),
        "ConsumedQuantity/ConsumedUnit are null on Unused rows",
    )
    checker.check(
        all(
            row["PricingQuantity"] and row["PricingUnit"] and row["SkuId"] and row["SkuPriceId"]
            for row in unused_rows
        ),
        "PricingQuantity, PricingUnit and Sku ids are populated on Unused rows",
    )
    checker.check(
        all(
            row["ResourceId"] and row["ResourceId"] != row["CommitmentDiscountId"]
            and row["ConsumedQuantity"] and row["ConsumedUnit"]
            and row["PricingCategory"] == "Committed"
            for row in used_rows
        ),
        "Used rows name a consuming resource and carry ConsumedQuantity/Unit",
    )

    # ContractedUnitPrice excludes commitment discounts.
    checker.check(
        all(_dec(row["ContractedCost"]) != _dec(row["EffectiveCost"]) for row in used_rows),
        "ContractedCost differs from EffectiveCost on Used rows (the commitment discount "
        "is not folded into the contracted price)",
        f"{sum(1 for r in used_rows if _dec(r['ContractedCost']) == _dec(r['EffectiveCost']))} rows",
    )
    checker.check(
        all(
            _dec(row["EffectiveCost"]) < _dec(row["ContractedCost"]) <= _dec(row["ListCost"])
            for row in used_rows
        ),
        "EffectiveCost < ContractedCost <= ListCost on Used rows",
    )

    # Commitment discount columns.
    commitment_rows = [
        row for row in rows
        if row["CommitmentDiscountId"] and row["ChargeCategory"] in ("Usage", "Purchase")
    ]
    checker.check(
        all(
            row["CommitmentDiscountQuantity"] and row["CommitmentDiscountUnit"]
            for row in commitment_rows
        ),
        "CommitmentDiscountQuantity/Unit populated on every commitment Usage/Purchase row",
    )
    checker.check(
        all(
            (row["CommitmentDiscountUnit"] == "USD")
            == (row["CommitmentDiscountCategory"] == "Spend")
            for row in commitment_rows
        ),
        "CommitmentDiscountUnit is USD exactly when the category is Spend",
    )

    # PricingQuantity / PricingUnit nullability.
    mismatched = [row for row in rows if bool(row["PricingQuantity"]) != bool(row["PricingUnit"])]
    checker.check(
        not mismatched,
        "PricingUnit is null if and only if PricingQuantity is",
        f"{len(mismatched)} rows",
    )
    missing_qty = [
        row for row in rows
        if row["ChargeCategory"] in ("Usage", "Purchase") and not row["PricingQuantity"]
    ]
    checker.check(
        not missing_qty,
        "PricingQuantity populated on every Usage/Purchase row",
        f"{len(missing_qty)} rows",
    )
    taxed = [row for row in rows if row["ChargeCategory"] == "Tax" and row["PricingQuantity"]]
    checker.check(not taxed, "PricingQuantity is null on Tax rows", f"{len(taxed)} rows")

    # Billing identity.
    names: dict[str, set[str]] = defaultdict(set)
    invoices: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        names[row["BillingAccountId"]].add(row["BillingAccountName"])
        invoices[row["BillingAccountId"]].add(row["InvoiceId"])
    checker.check(
        all(len(value) == 1 for value in names.values())
        and all(len(value) == 1 for value in invoices.values()),
        "each BillingAccountId maps to one BillingAccountName and one InvoiceId",
    )
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["CommitmentDiscountId"]:
            groups[row["CommitmentDiscountId"]].append(row)
    inconsistent = [
        commit_id
        for commit_id, group in groups.items()
        if any(len({row[field] for row in group}) > 1 for field in BILLING_IDENTITY)
    ]
    checker.check(
        not inconsistent,
        "every row of a commitment group shares one billing identity",
        f"{len(inconsistent)} of {len(groups)} groups differ",
    )

    # What the fixtures claim to contain.
    checker.check(
        not any(row["ChargeCategory"] == "Credit" for row in rows),
        "no Credit rows (they live behind --include-credits and are not committed)",
    )


def main() -> int:
    checker = Checker()
    for provider in PROVIDERS:
        check_provider(provider, checker)
    print()
    if checker.failures:
        print(f"{len(checker.failures)} check(s) failed")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
