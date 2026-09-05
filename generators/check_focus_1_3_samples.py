"""Acceptance checks for the committed FOCUS 1.3 samples.

Run from the repository root:

    python generators/check_focus_1_3_samples.py

Every check is a normative FOCUS 1.3 requirement or an invariant the samples claim
in ``FOCUS-1.3/README.md``. Exits non-zero if any check fails, so it can be wired
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

COST_AND_USAGE_COLUMNS = 65
CONTRACT_COMMITMENT_COLUMNS = 13

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
    path = ROOT / "generators" / f"generate_{provider}_focus_1_3.py"
    spec = importlib.util.spec_from_file_location(f"gen_{provider}", path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve annotations through sys.modules, so register first.
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
 'ServiceProviderName',
 'HostProviderName',
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
 'ContractApplied',
 'CapacityReservationId',
 'CapacityReservationStatus',
 'AllocatedMethodId',
 'AllocatedMethodDetails',
 'AllocatedResourceId',
 'AllocatedResourceName',
 'AllocatedTags',
 'Tags')
EXPECTED_CONTRACT_COLUMNS = ('ContractCommitmentId',
 'ContractCommitmentType',
 'ContractCommitmentCategory',
 'ContractCommitmentCost',
 'ContractCommitmentQuantity',
 'ContractCommitmentUnit',
 'ContractCommitmentDescription',
 'ContractCommitmentPeriodStart',
 'ContractCommitmentPeriodEnd',
 'ContractId',
 'ContractPeriodStart',
 'ContractPeriodEnd',
 'BillingCurrency')

# These checks read the exported data, independently of the generator helpers.
NEVER_NULL = (
    "ServiceProviderName", "HostProviderName", "ProviderName", "PublisherName", "InvoiceIssuerName", "BilledCost", "EffectiveCost",
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


def exact_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("non-finite JSON number")
    return json.loads(raw, parse_float=Decimal, parse_int=Decimal, parse_constant=invalid, object_pairs_hook=pairs)


def contract_semantic_errors(rows, provider, contracts):
    errors = []
    lookup = {r["ContractCommitmentId"]: r for r in contracts} if contracts is not None else {}
    for number, row in enumerate(rows, 1):
        try:
            if row["ContractApplied"]:
                obj = exact_json(row["ContractApplied"])
                if set(obj) != {"Elements"} or not isinstance(obj["Elements"], list) or len(obj["Elements"]) != 1:
                    raise ValueError("invalid ContractApplied root")
                e = obj["Elements"][0]
                required = {"ContractId", "ContractCommitmentId", "ContractCommitmentAppliedCost"}
                term = lookup.get(e.get("ContractCommitmentId"))
                usage = term["ContractCommitmentCategory"] == "Usage" if term else (
                    row["CommitmentDiscountCategory"] == "Usage" or e.get("ContractCommitmentId", "").endswith("COMPUTE-0003"))
                if usage:
                    required |= {"ContractCommitmentAppliedQuantity", "ContractCommitmentAppliedUnit"}
                if set(e) != required or not all(isinstance(e[k], str) and e[k] for k in ("ContractId", "ContractCommitmentId")):
                    raise ValueError("missing, unexpected or incorrectly typed ContractApplied key")
                for key in ("ContractCommitmentAppliedCost", "ContractCommitmentAppliedQuantity"):
                    if key in e and (not isinstance(e[key], Decimal) or not e[key].is_finite()):
                        raise ValueError("applied number must be finite Decimal")
                if term:
                    if not (term["ContractCommitmentPeriodStart"] <= row["ChargePeriodStart"]
                            < row["ChargePeriodEnd"] <= term["ContractCommitmentPeriodEnd"]):
                        raise ValueError("charge outside commitment period")
                    if usage and e["ContractCommitmentAppliedUnit"] != term["ContractCommitmentUnit"]:
                        raise ValueError("applied unit differs from contract unit")
                if not row["CommitmentDiscountId"]:
                    suffix = ("COMPUTE-0003" if row["ServiceName"] == COMPUTE_SERVICE[provider]
                              else "STORAGE-0002" if row["ServiceName"] == STORAGE_SERVICE[provider] else "SPEND-0001")
                    if not e["ContractCommitmentId"].endswith(suffix):
                        raise ValueError("negotiated term does not apply to this service")
            if row["ChargeCategory"] == "Usage" and row["PricingCategory"] == "Standard":
                rate = Decimal("0.9") if row["ContractApplied"] else Decimal(1)
                if Decimal(row["ContractedUnitPrice"]) != (Decimal(row["ListUnitPrice"]) * rate).quantize(Decimal("0.0000000001"), rounding="ROUND_HALF_UP"):
                    raise ValueError("public/negotiated price does not match the applied contract")
            if row["AllocatedMethodDetails"]:
                obj = exact_json(row["AllocatedMethodDetails"])
                if set(obj) != {"Elements"} or not isinstance(obj["Elements"], list) or len(obj["Elements"]) != 1:
                    raise ValueError("invalid allocation root")
                e = obj["Elements"][0]
                keys = {"AllocatedRatio", "UsageQuantity", "UsageUnit"}
                if not keys <= set(e) or any(k not in keys and not k.startswith("x_") for k in e):
                    raise ValueError("invalid allocation keys")
                if not isinstance(e["AllocatedRatio"], Decimal) or e["AllocatedRatio"] != 1:
                    raise ValueError("fixture allocation must have ratio one")
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            errors.append(f"contract: record {number}: {exc}")
    for term in lookup.values():
        if not (term["ContractPeriodStart"] <= term["ContractCommitmentPeriodStart"]
                < term["ContractCommitmentPeriodEnd"] <= term["ContractPeriodEnd"]):
            errors.append("contract: invalid contract/commitment period")
        linked = next((r for r in rows if r["CommitmentDiscountId"] == term["ContractCommitmentId"]), None)
        if linked:
            if Decimal(term["ContractCommitmentCost"]) != HOURLY_COMMITMENT[provider] * 8760:
                errors.append("contract: annual cost does not cover the 500-unit fleet")
            if term["ContractCommitmentCategory"] == "Usage" and Decimal(term["ContractCommitmentQuantity"]) != 500 * 8760:
                errors.append("contract: annual quantity does not cover the 500-unit fleet")
    return errors


def audit_rows(rows: list[dict[str, str]], provider: str,
               contracts: list[dict[str, str]] | None = None) -> list[str]:
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
            allocated_id = row.get("AllocatedResourceId", "")
            if provider == "aws" and allocated_id and allocated_id.split(":", 5)[4] != row["SubAccountId"]:
                errors.append(f"resource: record {number} has the wrong allocation owner")
            if row.get("ContractApplied"):
                elements = json.loads(row["ContractApplied"], parse_float=Decimal, parse_int=Decimal)["Elements"]
                if len(elements) != 1:
                    errors.append(f"contract: record {number} is outside the single-element fixture model")
                for element in elements:
                    cost = element.get("ContractCommitmentAppliedCost")
                    quantity = element.get("ContractCommitmentAppliedQuantity")
                    unit = element.get("ContractCommitmentAppliedUnit")
                    if not isinstance(cost, Decimal) or not cost.is_finite() or cost != Decimal(row["EffectiveCost"]):
                        errors.append(f"contract: record {number} applied cost differs from row cost")
                    if quantity is not None:
                        if (not isinstance(quantity, Decimal) or not quantity.is_finite()
                            or quantity != Decimal(row["PricingQuantity"]) or unit != row["PricingUnit"]):
                            errors.append(f"contract: record {number} applied quantity/unit differs from row")
                    elif "ContractCommitmentAppliedQuantity" in element or "ContractCommitmentAppliedUnit" in element:
                        errors.append(f"contract: record {number} must omit inapplicable quantity/unit")
            if row.get("AllocatedMethodDetails"):
                elements = json.loads(row["AllocatedMethodDetails"], parse_float=Decimal, parse_int=Decimal)["Elements"]
                for element in elements:
                    if (not isinstance(element["UsageQuantity"], Decimal)
                        or element["UsageQuantity"] != Decimal(row["ConsumedQuantity"])
                        or element["UsageUnit"] != row["ConsumedUnit"]):
                        errors.append(f"contract: record {number} has inconsistent allocation quantity/unit")
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
    errors.extend(contract_semantic_errors(rows, provider, contracts))
    if contracts is not None:
        lookup = {}
        for contract in contracts:
            if tuple(contract) != EXPECTED_CONTRACT_COLUMNS:
                errors.append("contract: wrong contract column names/order")
            key = contract["ContractCommitmentId"]
            if key in lookup:
                errors.append(f"contract: duplicate commitment {key}")
            lookup[key] = contract
            quantity = contract["ContractCommitmentQuantity"]
            if quantity and ("." not in quantity or not Decimal(quantity).is_finite()):
                errors.append(f"contract: {key} quantity lacks decimal serialization")
        for row in rows:
            if not row.get("ContractApplied"):
                continue
            for element in json.loads(row["ContractApplied"])["Elements"]:
                contract = lookup.get(element.get("ContractCommitmentId"))
                if contract is None or contract["ContractId"] != element.get("ContractId"):
                    errors.append("contract: applied commitment does not join to the correct contract")
    return errors


def check_provider(provider: str, checker: Checker) -> None:
    print(f"\n{provider.upper()}")
    module = _load(provider)
    cu_path = ROOT / "FOCUS-1.3" / f"focus_sample_costandusage_{provider}_1000.csv"
    cc_path = ROOT / "FOCUS-1.3" / f"focus_sample_contractcommitment_{provider}.csv"
    cu = _rows(cu_path)
    cc = _rows(cc_path)

    failures = audit_rows(cu, provider, cc)
    for category in ("required", "cost", "tax", "sku", "resource", "commitment", "contract"):
        found = [error for error in failures if error.startswith(category + ":")]
        checker.check(not found, f"independent {category} invariants", "; ".join(found[:5]))

    # 1. Determinism: the committed files are exactly what the generator emits.
    metrics = fixture_metrics(cu, provider)
    checker.check(Decimal(metrics["commitment_share"]) >= Decimal("0.05"),
                  "default fleet commitments represent at least 5% of billed cost [fixture target]")
    checker.check(all(Decimal(0) <= Decimal(metrics[k]) <= 1 for k in ("utilization", "waste", "coverage")),
                  "fleet utilization, waste and eligible-compute coverage are bounded")

    checker.check(
        module.generate_csv_bytes(1000, 1302) == cu_path.read_bytes(),
        "cost and usage file is byte-reproducible",
    )
    checker.check(
        module.generate_contract_commitment_csv_bytes(1000, 1302) == cc_path.read_bytes(),
        "contract commitment file is byte-reproducible",
    )

    # 2. Column sets: FOCUS 1.3, not 1.4.
    checker.check(len(cu[0]) == COST_AND_USAGE_COLUMNS, "cost and usage has 65 columns")
    checker.check(
        len(cc[0]) == CONTRACT_COMMITMENT_COLUMNS,
        "contract commitment has 13 columns",
        f"got {len(cc[0])}",
    )

    # 3. ListCost/ContractedCost MUST equal price x PricingQuantity, exactly.
    for cost_col, price_col in (
        ("ListCost", "ListUnitPrice"),
        ("ContractedCost", "ContractedUnitPrice"),
    ):
        bad = [
            row
            for row in cu
            if row[price_col] and row["PricingQuantity"]
            and _dec(row[cost_col]) != _dec(row[price_col]) * _dec(row["PricingQuantity"])
        ]
        checker.check(
            not bad,
            f"{cost_col} == {price_col} x PricingQuantity where unit pricing applies",
            f"{len(bad)} rows differ",
        )

    # 4. Commitment reconciliation. The normative requirement is per
    #    CommitmentDiscountId, over the whole commitment. Grouping by charge period as
    #    well is an additional invariant of these fixtures — the recurring model makes
    #    every single period balance — and it catches periods that would otherwise
    #    cancel each other out.
    def _reconcile(key_fields, label: str) -> None:
        purchases: dict[tuple, Decimal] = defaultdict(Decimal)
        usage: dict[tuple, Decimal] = defaultdict(Decimal)
        for row in cu:
            if not row["CommitmentDiscountId"]:
                continue
            key = tuple(row[field] for field in key_fields)
            if row["ChargeCategory"] == "Purchase":
                purchases[key] += _dec(row["BilledCost"])
            elif row["ChargeCategory"] == "Usage":
                usage[key] += _dec(row["EffectiveCost"])
        keys = set(purchases) | set(usage)
        bad = [key for key in keys if purchases[key] != usage[key]]
        checker.check(
            not bad,
            label,
            f"{len(bad)} of {len(keys)} groups unbalanced",
        )

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
    for row in cu:
        if row["CommitmentDiscountId"] and row["ChargeCategory"] == "Usage":
            usage_total += _dec(row["EffectiveCost"])
            by_status[row["CommitmentDiscountStatus"]] += _dec(row["EffectiveCost"])
    checker.check(
        usage_total == by_status["Used"] + by_status["Unused"] and set(by_status) == {"Used", "Unused"},
        "usage EffectiveCost splits into Used + Unused, and nothing else",
        f"statuses seen: {sorted(by_status)}",
    )

    # 5. The shape of a commitment purchase row.
    purchase_rows = [
        row
        for row in cu
        if row["ChargeCategory"] == "Purchase" and row["CommitmentDiscountId"]
    ]
    checker.check(bool(purchase_rows), "the dataset contains commitment purchase rows")
    checker.check(
        all(row["ChargeFrequency"] == "Recurring" for row in purchase_rows),
        "commitment purchases are Recurring, amortised per charge period",
    )
    checker.check(
        all(row["PricingCategory"] == "Standard" for row in purchase_rows),
        "commitment purchases carry PricingCategory Standard",
    )
    checker.check(
        all(row["ResourceId"] == row["CommitmentDiscountId"] for row in purchase_rows),
        "commitment purchases carry the commitment id as ResourceId",
    )
    checker.check(
        all(_dec(row["EffectiveCost"]) == 0 for row in purchase_rows),
        "commitment purchases have EffectiveCost 0",
    )

    # 6. The shape of an Unused row, per the FOCUS commitment-discount scenarios.
    unused_rows = [row for row in cu if row["CommitmentDiscountStatus"] == "Unused"]
    used_rows = [row for row in cu if row["CommitmentDiscountStatus"] == "Used"]
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
        all(row["PricingQuantity"] and row["PricingUnit"] and row["SkuId"] and row["SkuPriceId"]
            for row in unused_rows),
        "PricingQuantity, PricingUnit and Sku ids are populated on Unused rows",
    )

    # 7. Used rows draw the commitment down against a resource.
    checker.check(
        all(
            row["ResourceId"] and row["ResourceId"] != row["CommitmentDiscountId"]
            and row["ConsumedQuantity"] and row["ConsumedUnit"]
            and row["PricingCategory"] == "Committed"
            for row in used_rows
        ),
        "Used rows name a consuming resource and carry ConsumedQuantity/Unit",
    )

    # 8. ContractedUnitPrice excludes the commitment discount: on a Used row the
    #    commitment saving must sit between ContractedCost and EffectiveCost.
    committed_used = [row for row in used_rows if row["ContractedUnitPrice"]]
    checker.check(
        all(_dec(row["ContractedCost"]) != _dec(row["EffectiveCost"]) for row in committed_used),
        "ContractedCost differs from EffectiveCost on Used rows (the commitment discount "
        "is not folded into the contracted price)",
        f"{sum(1 for r in committed_used if _dec(r['ContractedCost']) == _dec(r['EffectiveCost']))} rows",
    )
    checker.check(
        all(
            _dec(row["EffectiveCost"]) < _dec(row["ContractedCost"]) <= _dec(row["ListCost"])
            for row in committed_used
        ),
        "EffectiveCost < ContractedCost <= ListCost on Used rows",
    )

    # 9. Commitment discount columns, everywhere they are required.
    commitment_rows = [
        row
        for row in cu
        if row["CommitmentDiscountId"] and row["ChargeCategory"] in ("Usage", "Purchase")
    ]
    checker.check(
        all(row["CommitmentDiscountQuantity"] and row["CommitmentDiscountUnit"]
            for row in commitment_rows),
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

    # 10. PricingUnit is null if and only if PricingQuantity is.
    mismatched = [row for row in cu if bool(row["PricingQuantity"]) != bool(row["PricingUnit"])]
    checker.check(
        not mismatched,
        "PricingUnit is null if and only if PricingQuantity is",
        f"{len(mismatched)} rows",
    )
    missing_qty = [
        row for row in cu
        if row["ChargeCategory"] in ("Usage", "Purchase") and not row["PricingQuantity"]
    ]
    checker.check(
        not missing_qty,
        "PricingQuantity populated on every Usage/Purchase row",
        f"{len(missing_qty)} rows",
    )

    # 11. Billing identity: one name and one invoice per billing account, and a single
    #     identity within each commitment group.
    names: dict[str, set[str]] = defaultdict(set)
    invoices: dict[str, set[str]] = defaultdict(set)
    for row in cu:
        names[row["BillingAccountId"]].add(row["BillingAccountName"])
        invoices[row["BillingAccountId"]].add(row["InvoiceId"])
    checker.check(
        all(len(value) == 1 for value in names.values())
        and all(len(value) == 1 for value in invoices.values()),
        "each BillingAccountId maps to one BillingAccountName and one InvoiceId",
    )
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in cu:
        if row["CommitmentDiscountId"]:
            groups[row["CommitmentDiscountId"]].append(row)
    inconsistent = [
        commit_id
        for commit_id, rows in groups.items()
        if any(len({row[field] for row in rows}) > 1 for field in BILLING_IDENTITY)
    ]
    checker.check(
        not inconsistent,
        "every row of a commitment group shares one billing identity",
        f"{len(inconsistent)} of {len(groups)} groups differ",
    )

    # 12. ContractApplied shape.
    applied_ids: set[str] = set()
    shape_errors: list[str] = []
    for row in cu:
        raw = row["ContractApplied"]
        if not raw:
            continue
        for element in json.loads(raw)["Elements"]:
            applied_ids.add(element["ContractCommitmentId"])
            if "ContractId" not in element:
                shape_errors.append("missing ContractId")
            if not isinstance(element["ContractCommitmentAppliedCost"], (int, float)):
                shape_errors.append("AppliedCost is not a JSON number")
            quantity = element.get("ContractCommitmentAppliedQuantity")
            unit = element.get("ContractCommitmentAppliedUnit")
            if quantity is None and unit is not None:
                shape_errors.append("AppliedUnit present without AppliedQuantity")
            if quantity is not None and not isinstance(quantity, (int, float)):
                shape_errors.append("AppliedQuantity is not a JSON number")
            if unit is not None and not isinstance(unit, str):
                shape_errors.append("AppliedUnit is not a string")
    checker.check(
        not shape_errors,
        "ContractApplied elements are well formed",
        "; ".join(sorted(set(shape_errors))),
    )
    checker.check(bool(applied_ids), "ContractApplied is populated on at least one row")

    # 13. The join, and the fact that the dataset carries more than commitment discounts.
    commitment_ids = {row["ContractCommitmentId"] for row in cc}
    dangling = applied_ids - commitment_ids
    checker.check(
        not dangling,
        "every ContractCommitmentId in ContractApplied exists in the Contract Commitment file",
        f"dangling: {sorted(dangling)[:3]}",
    )
    discount_ids = {row["CommitmentDiscountId"] for row in cu if row["CommitmentDiscountId"]}
    non_discount = commitment_ids - discount_ids
    checker.check(
        bool(non_discount),
        "at least one commitment is not a commitment discount",
        "the dataset only restates CommitmentDiscountId",
    )
    checker.check(
        non_discount <= applied_ids,
        "non-commitment-discount commitments are still reachable through ContractApplied",
    )
    per_contract: dict[str, set[str]] = defaultdict(set)
    for row in cc:
        per_contract[row["ContractId"]].add(row["ContractCommitmentId"])
    checker.check(
        any(len(ids) > 1 for ids in per_contract.values()),
        "at least one ContractId carries several commitments",
    )

    # 14. Contract Commitment conditional nullability.
    spend_without_cost = [
        row for row in cc
        if row["ContractCommitmentCategory"] == "Spend" and not row["ContractCommitmentCost"]
    ]
    checker.check(
        not spend_without_cost,
        "ContractCommitmentCost populated when the category is Spend",
        f"{len(spend_without_cost)} rows",
    )
    usage_without_qty = [
        row
        for row in cc
        if row["ContractCommitmentCategory"] == "Usage"
        and not (row["ContractCommitmentQuantity"] and row["ContractCommitmentUnit"])
    ]
    checker.check(
        not usage_without_qty,
        "ContractCommitmentQuantity/Unit populated when the category is Usage",
        f"{len(usage_without_qty)} rows",
    )
    bad_span = [
        row
        for row in cc
        if not (
            row["ContractPeriodStart"] <= row["ContractCommitmentPeriodStart"]
            and row["ContractPeriodEnd"] >= row["ContractCommitmentPeriodEnd"]
        )
    ]
    checker.check(
        not bad_span,
        "the contract period encloses the commitment period",
        f"{len(bad_span)} rows",
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
