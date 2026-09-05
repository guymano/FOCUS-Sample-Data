"""FOCUS 1.3 contracts and allocations on the same common scenario engine."""

from __future__ import annotations
import csv
import io
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from .base import VersionAdapter
from ..values import (
    PRICING_CATEGORIES,
    FOCUS_SKU_PRICE_KEYS,
    _BILLING_IDENTITY_KEYS,
    _BILLING_START,
    _BILLING_END,
    _PERIOD_DAYS,
    _PERIOD_HOURS,
    _COST_Q,
    _PRICE_Q,
    _QTY_Q,
    _EUR_PER_USD,
    _COMMIT_RATE,
    _PRIVATE_RATE,
    _FLEET_SIZE,
    _COMMIT_TERM_HOURS,
    _ENVIRONMENTS,
    _COST_CENTERS,
    _OWNERS,
    _q,
    _s,
    _iso,
    _hexid,
    _period,
    _trim,
    _s_cost,
    _stable_id,
    _decimal_json,
    _s_decimal,
)

DEFAULT_ROWS = 1000
_COMMIT_TERM_DAYS = 365
_NEGOTIATED_PERIOD_START = _BILLING_START - timedelta(days=90)

COLUMNS: tuple[str, ...] = (
    "ProviderName",
    "PublisherName",
    "ServiceProviderName",
    "HostProviderName",
    "InvoiceIssuerName",
    "InvoiceId",
    "BillingAccountId",
    "BillingAccountName",
    "BillingAccountType",
    "SubAccountId",
    "SubAccountName",
    "SubAccountType",
    "BillingPeriodStart",
    "BillingPeriodEnd",
    "ChargePeriodStart",
    "ChargePeriodEnd",
    "ChargeCategory",
    "ChargeClass",
    "ChargeDescription",
    "ChargeFrequency",
    "BilledCost",
    "EffectiveCost",
    "ListCost",
    "ContractedCost",
    "ListUnitPrice",
    "ContractedUnitPrice",
    "PricingCategory",
    "PricingQuantity",
    "PricingUnit",
    "PricingCurrency",
    "PricingCurrencyContractedUnitPrice",
    "PricingCurrencyEffectiveCost",
    "PricingCurrencyListUnitPrice",
    "BillingCurrency",
    "ConsumedQuantity",
    "ConsumedUnit",
    "ServiceName",
    "ServiceCategory",
    "ServiceSubcategory",
    "SkuId",
    "SkuMeter",
    "SkuPriceId",
    "SkuPriceDetails",
    "ResourceId",
    "ResourceName",
    "ResourceType",
    "RegionId",
    "RegionName",
    "AvailabilityZone",
    "CommitmentDiscountId",
    "CommitmentDiscountName",
    "CommitmentDiscountCategory",
    "CommitmentDiscountType",
    "CommitmentDiscountStatus",
    "CommitmentDiscountQuantity",
    "CommitmentDiscountUnit",
    "ContractApplied",
    "CapacityReservationId",
    "CapacityReservationStatus",
    "AllocatedMethodId",
    "AllocatedMethodDetails",
    "AllocatedResourceId",
    "AllocatedResourceName",
    "AllocatedTags",
    "Tags",
)

CONTRACT_COMMITMENT_COLUMNS: tuple[str, ...] = (
    "ContractCommitmentId",
    "ContractCommitmentType",
    "ContractCommitmentCategory",
    "ContractCommitmentCost",
    "ContractCommitmentQuantity",
    "ContractCommitmentUnit",
    "ContractCommitmentDescription",
    "ContractCommitmentPeriodStart",
    "ContractCommitmentPeriodEnd",
    "ContractId",
    "ContractPeriodStart",
    "ContractPeriodEnd",
    "BillingCurrency",
)

_ALLOCATION_METHODS: tuple[tuple[str, dict[str, object]], ...] = (
    ("split-proportional", {"x_Strategy": "Proportional", "x_Basis": "vCPUSeconds"}),
    ("split-even", {"x_Strategy": "Even", "x_Basis": "Workloads"}),
    ("split-weighted", {"x_Strategy": "Weighted", "x_Basis": "MemoryBytes"}),
)

_ALLOCATION_WORKLOADS = ("checkout", "search", "billing", "analytics", "ingestion")


@dataclass(frozen=True)
class _ContractCommitment:
    """One commitment term of a contract â€” one row of the FOCUS 1.3 Contract
    Commitment dataset (13 columns; the wider column set only arrives in 1.4)."""

    commitment_id: str
    contract_id: str
    commitment_type: str
    category: str  # "Spend" | "Usage"
    cost: Decimal | None
    quantity: Decimal | None
    unit: str | None
    description: str
    period_start: datetime
    period_end: datetime


class _ContractRegistry:
    """Single source of truth for the Contract Commitment dataset.

    Commitment terms are recorded while the Cost and Usage rows are built, so the two
    datasets cannot drift: the Contract Commitment CSV is written from these entries
    instead of being re-derived from the Cost and Usage rows.
    """

    _PER_CONTRACT = 3  # commitment discounts grouped under one master agreement

    def __init__(self, profile) -> None:
        self.commitments: list[_ContractCommitment] = []
        self._sequence = 0
        self._within_contract = 0
        for (
            commitment_id,
            kind,
            category,
            cost,
            quantity,
            unit,
            description,
        ) in profile.negotiated_terms:
            self.commitments.append(
                _ContractCommitment(
                    commitment_id=commitment_id,
                    contract_id=profile.negotiated_contract_id,
                    commitment_type=kind,
                    category=category,
                    cost=cost,
                    quantity=quantity,
                    unit=unit,
                    description=description,
                    period_start=_NEGOTIATED_PERIOD_START,
                    period_end=_NEGOTIATED_PERIOD_START
                    + timedelta(days=_COMMIT_TERM_DAYS),
                )
            )

    def next_contract_id(self) -> tuple[str, int]:
        """Contract id for the next commitment discount, plus its rank inside that
        contract, so several commitments share one agreement."""
        if self._within_contract == 0:
            self._sequence += 1
        rank = self._within_contract
        self._within_contract = (self._within_contract + 1) % self._PER_CONTRACT
        return f"CONTRACT-CD-{self._sequence:04d}", rank

    def add(self, commitment: _ContractCommitment) -> None:
        self.commitments.append(commitment)


def _contract_applied(
    commit_id: str,
    contract_id: str,
    applied_cost: Decimal,
    applied_qty: Decimal | None = None,
    applied_unit: str | None = None,
) -> str:
    """FOCUS 1.3 ``ContractApplied``: an Elements array linking the row to the
    Contract Commitment dataset.

    The keys follow FOCUS_Spec erratum #3 (``ContractId`` / ``ContractCommitmentId``,
    not the ``...ID`` spelling still printed in the v1.3 text) and the 1.3.0.1 rule
    model. ``ContractCommitmentAppliedCost`` and ``...AppliedQuantity`` are Decimal and
    stay JSON numbers; ``...AppliedUnit`` is a string (erratum #2) and MUST be absent
    whenever the quantity is â€” which is the Spend case, since a spend commitment is
    drawn down in currency and carries no quantity.
    """
    element: dict[str, object] = {
        "ContractId": contract_id,
        "ContractCommitmentId": commit_id,
        "ContractCommitmentAppliedCost": applied_cost,
    }
    if applied_qty is not None:
        element["ContractCommitmentAppliedQuantity"] = applied_qty
        element["ContractCommitmentAppliedUnit"] = applied_unit
    return _decimal_json({"Elements": [element]})


def split_row(engine, rng: random.Random, i: int) -> dict[str, str]:
    """A Split Cost Allocation row (FOCUS 1.3): a shared resource's cost allocated
    to a consuming workload. ``ResourceId`` is the shared resource; the
    ``Allocated*`` columns name the workload that received the split."""
    spec = engine.profile.services[0]  # shared compute host split across workloads
    region_id, region_name, azs = rng.choice(engine.profile.regions)
    row, ctx = engine._base_row(rng)
    start, end = _period(i, "hourly")
    row["ChargePeriodStart"], row["ChargePeriodEnd"] = start, end
    engine._set_service(row, spec)
    shared_name = f"shared-host-{_hexid(rng, 8)}"
    engine._set_resource_sku(rng, row, spec, ctx, region_id, region_name, shared_name)
    row["AvailabilityZone"] = rng.choice(azs)

    quantity = _q(Decimal(rng.uniform(0.05, 1.0)), _QTY_Q)
    list_unit = _q(spec.unit_price_usd, _PRICE_Q)
    contracted_unit = list_unit  # public rate: no negotiated contract applies
    # Exact products: FOCUS requires ListCost == ListUnitPrice x PricingQuantity
    # and ContractedCost == ContractedUnitPrice x PricingQuantity.
    list_cost = list_unit * quantity
    contracted_cost = contracted_unit * quantity

    row["ChargeCategory"] = "Usage"
    row["ChargeFrequency"] = "Usage-Based"
    row["ChargeDescription"] = engine.profile.allocation_description
    row["PricingCategory"] = "Standard"
    row["BilledCost"] = _s_cost(contracted_cost)
    row["EffectiveCost"] = _s_cost(contracted_cost)
    row["ListCost"] = _s_cost(list_cost)
    row["ContractedCost"] = _s_cost(contracted_cost)
    row["ListUnitPrice"] = _s(list_unit)
    row["ContractedUnitPrice"] = _s(contracted_unit)
    row["PricingQuantity"] = _s(quantity)
    row["PricingUnit"] = spec.pricing_unit
    row["ConsumedQuantity"] = _s(quantity)
    row["ConsumedUnit"] = spec.pricing_unit
    # Split-allocated on-demand cost: no contract applied -> ContractApplied null.

    workload = rng.choice(_ALLOCATION_WORKLOADS)
    method_id, method_details = rng.choice(_ALLOCATION_METHODS)
    alloc_name = f"workload-{workload}"
    row["AllocatedMethodId"] = method_id
    # FOCUS 1.3 split allocation details: an Elements array, each entry exposing the
    # allocated ratio and the usage that drove the split (plus x_ method metadata).
    element = {
        "AllocatedRatio": Decimal("1"),
        "UsageUnit": spec.pricing_unit,
        "UsageQuantity": quantity,
        **method_details,
    }
    row["AllocatedMethodDetails"] = _decimal_json({"Elements": [element]})
    row["AllocatedResourceId"] = engine.profile.allocation_id(
        rng, region_id, ctx, workload
    )
    row["AllocatedResourceName"] = alloc_name
    row["AllocatedTags"] = json.dumps(
        {"workload": workload, engine.profile.tag_keys[1]: rng.choice(_COST_CENTERS)},
        separators=(",", ":"),
    )
    engine._set_currency(row, "USD", list_unit, contracted_unit, contracted_cost)
    return row


def generate_contract_commitment_rows(
    engine,
    rows: int = DEFAULT_ROWS,
    seed: int = 1302,
) -> list[dict[str, str]]:
    """Return the FOCUS 1.3 Contract Commitment dataset for the same (rows, seed).

    Built from the registry filled while the Cost and Usage rows are generated, so the
    two datasets cannot drift. It carries more than commitment discounts: the
    negotiated terms of the master agreement have no ``CommitmentDiscountId`` at all
    and reach Cost and Usage only through ``ContractApplied``.
    """
    registry = _ContractRegistry(engine.profile)
    engine.generate_rows(rows, seed, registry=registry)

    # A contract's period encloses the periods of the commitments it carries.
    spans: dict[str, tuple[datetime, datetime]] = {}
    for commitment in registry.commitments:
        start, end = spans.get(
            commitment.contract_id, (commitment.period_start, commitment.period_end)
        )
        spans[commitment.contract_id] = (
            min(start, commitment.period_start),
            max(end, commitment.period_end),
        )

    out: list[dict[str, str]] = []
    for commitment in registry.commitments:
        contract_start, contract_end = spans[commitment.contract_id]
        row = {name: "" for name in CONTRACT_COMMITMENT_COLUMNS}
        row["ContractCommitmentId"] = commitment.commitment_id
        row["ContractCommitmentType"] = commitment.commitment_type
        row["ContractCommitmentCategory"] = commitment.category
        # Cost MUST NOT be null when the category is Spend; Quantity and Unit MUST NOT
        # be null when it is Usage. A spend commitment is drawn down in currency, so it
        # carries no quantity at all.
        row["ContractCommitmentCost"] = (
            "" if commitment.cost is None else _s_cost(commitment.cost)
        )
        row["ContractCommitmentQuantity"] = (
            "" if commitment.quantity is None else _s_decimal(commitment.quantity)
        )
        row["ContractCommitmentUnit"] = commitment.unit or ""
        row["ContractCommitmentDescription"] = commitment.description
        row["ContractCommitmentPeriodStart"] = _iso(commitment.period_start)
        row["ContractCommitmentPeriodEnd"] = _iso(commitment.period_end)
        row["ContractId"] = commitment.contract_id
        row["ContractPeriodStart"] = _iso(contract_start)
        row["ContractPeriodEnd"] = _iso(contract_end)
        row["BillingCurrency"] = "USD"
        out.append(row)
    return out


def generate_contract_commitment_csv_bytes(
    engine,
    rows: int = DEFAULT_ROWS,
    seed: int = 1302,
) -> bytes:
    """Serialise the Contract Commitment dataset to deterministic UTF-8 CSV bytes (LF)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=list(CONTRACT_COMMITMENT_COLUMNS), lineterminator="\n"
    )
    writer.writeheader()
    for record in generate_contract_commitment_rows(engine, rows, seed):
        writer.writerow(record)
    return buffer.getvalue().encode("utf-8")


@dataclass(frozen=True)
class ContractAdapter(VersionAdapter):
    def fill_identity(self, row, profile):
        row["ServiceProviderName"] = profile.provider_name
        row["HostProviderName"] = profile.provider_name
        row["PricingCurrency"] = "USD"

    def select_contract(self, rng):
        return rng.random() < 0.35

    def apply_negotiated(self, row, profile, selected, spec, quantity, cost):
        if not selected:
            return
        if spec.name == profile.services[0].name:
            term = next(term for term in profile.negotiated_terms if term[2] == "Usage")
            row["ContractApplied"] = _contract_applied(
                term[0],
                profile.negotiated_contract_id,
                cost,
                quantity,
                spec.pricing_unit,
            )
        else:
            suffix = (
                "STORAGE-0002"
                if spec.name == profile.services[1].name
                else "SPEND-0001"
            )
            term = next(
                term for term in profile.negotiated_terms if term[0].endswith(suffix)
            )
            row["ContractApplied"] = _contract_applied(
                term[0], profile.negotiated_contract_id, cost
            )

    def new_registry(self, profile):
        return _ContractRegistry(profile)

    def record_commitment(
        self, registry, commit_id, kind, category, rate, spend, unit, name
    ):
        contract_id, term_rank = registry.next_contract_id()
        commit_period_start = _BILLING_START - timedelta(days=30 * term_rank)
        registry.add(
            _ContractCommitment(
                commitment_id=commit_id,
                contract_id=contract_id,
                commitment_type=kind,
                category=category,
                # The Contract Commitment dataset describes the whole term, not the slice of
                # it this fixture happens to cover.
                cost=rate * _COMMIT_TERM_HOURS,
                quantity=None if spend else _FLEET_SIZE * _COMMIT_TERM_HOURS,
                unit=None if spend else unit,
                description=name,
                period_start=commit_period_start,
                period_end=commit_period_start + timedelta(days=_COMMIT_TERM_DAYS),
            )
        )

        return contract_id

    def apply_commitment(
        self, row, contract_id, commit_id, rate, spend, quantity, unit
    ):
        row["ContractApplied"] = _contract_applied(
            commit_id,
            contract_id,
            rate,
            None if spend else quantity,
            None if spend else unit,
        )

    def split_row(self, engine, rng, index):
        return split_row(engine, rng, index)


ADAPTER = ContractAdapter("1.3", COLUMNS, 1302, 0.40, 0.43, CONTRACT_COMMITMENT_COLUMNS)
