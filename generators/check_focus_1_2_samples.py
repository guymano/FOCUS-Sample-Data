"""Acceptance checks for the committed FOCUS 1.2 samples.

Run from the repository root:

    python generators/check_focus_1_2_samples.py

Every check is a normative FOCUS 1.2 requirement or an invariant the samples claim
in ``FOCUS-1.2/README.md``. Exits non-zero if any check fails, so it can be wired
into CI.
"""

from __future__ import annotations

import csv
import importlib.util
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


def check_provider(provider: str, checker: Checker) -> None:
    print(f"\n{provider.upper()}")
    module = _load(provider)
    path = ROOT / "FOCUS-1.2" / f"focus_sample_costandusage_{provider}_1000.csv"
    rows = _rows(path)

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
            f"{cost_col} == {price_col} x PricingQuantity on every row",
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
