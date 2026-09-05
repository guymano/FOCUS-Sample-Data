"""One corrected implementation of each common scenario, used by all providers/versions.

The engine is immutable; RNG, tax lineage and contract registries belong to each call.
"""

from __future__ import annotations
import csv
import io
import json
import random
from dataclasses import dataclass
from decimal import Decimal
from .profiles.types import ProviderProfile, ServiceSpec as _ServiceSpec
from .values import (
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


@dataclass(frozen=True)
class Engine:
    profile: ProviderProfile
    adapter: object

    def _base_row(self, rng: random.Random) -> tuple[dict[str, str], dict[str, str]]:
        """Return (row, ctx) with identity/account/period-independent fields filled."""
        billing_id, billing_name = rng.choice(self.profile.billing_accounts)
        sub_id, sub_name = rng.choice(self.profile.sub_accounts)
        row = {name: "" for name in self.adapter.columns}
        row["ProviderName"] = self.profile.provider_name
        row["PublisherName"] = self.profile.publisher_name
        row["InvoiceIssuerName"] = self.profile.invoice_issuer
        row["InvoiceId"] = self.profile.invoice_id(billing_id)
        row["BillingAccountId"] = billing_id
        row["BillingAccountName"] = billing_name
        row["BillingAccountType"] = self.profile.billing_type
        row["SubAccountId"] = sub_id
        row["SubAccountName"] = sub_name
        row["SubAccountType"] = self.profile.sub_type
        row["BillingPeriodStart"] = _iso(_BILLING_START)
        row["BillingPeriodEnd"] = _iso(_BILLING_END)
        row["BillingCurrency"] = "USD"
        self.adapter.fill_identity(row, self.profile)
        row["Tags"] = json.dumps(
            {
                self.profile.tag_keys[0]: rng.choice(_ENVIRONMENTS),
                self.profile.tag_keys[1]: rng.choice(_COST_CENTERS),
                self.profile.tag_keys[2]: rng.choice(_OWNERS),
            },
            separators=(",", ":"),
        )
        return (row, {"billing_id": billing_id, "sub_id": sub_id, "sub_name": sub_name})

    def _set_service(self, row: dict[str, str], spec: _ServiceSpec) -> None:
        row["ServiceName"] = spec.name
        row["ServiceCategory"] = spec.category
        row["ServiceSubcategory"] = spec.subcategory

    def _set_resource_sku(
        self,
        rng: random.Random,
        row: dict[str, str],
        spec: _ServiceSpec,
        ctx: dict[str, str],
        region_id: str,
        region_name: str,
        resource_name: str,
    ) -> None:
        row["RegionId"] = region_id
        row["RegionName"] = region_name
        row["ResourceId"] = self.profile.resource_id(
            rng, spec, region_id, ctx, resource_name
        )
        row["ResourceName"] = resource_name
        row["ResourceType"] = spec.resource_type
        row["SkuMeter"] = spec.sku_meter
        row["SkuPriceDetails"] = json.dumps(
            dict(spec.sku_details), separators=(",", ":")
        )

    def _set_sku_ids(self, row: dict[str, str]) -> None:
        """Identify an offer and its list price, never a row, account or contract."""
        details = json.loads(row["SkuPriceDetails"])
        for key in details:
            if key.startswith("x_") and key[2:] in FOCUS_SKU_PRICE_KEYS:
                raise ValueError(f"Use the FOCUS-defined SKU property {key[2:]}")
            if not key.startswith("x_") and key not in FOCUS_SKU_PRICE_KEYS:
                raise ValueError(f"Custom SKU property requires x_ prefix: {key}")
        row["SkuId"] = _stable_id(
            "SKU-",
            [
                self.profile.provider_name,
                row["ServiceName"],
                row["SkuMeter"],
                row["RegionId"],
                row["PricingUnit"],
                details,
            ],
        )
        row["SkuPriceId"] = _stable_id(
            "SPRICE-",
            [
                row["SkuId"],
                row["BillingCurrency"],
                row["PricingCurrency"],
                _s_cost(Decimal(row["ListUnitPrice"])),
                _s_cost(Decimal(row["PricingCurrencyListUnitPrice"])),
            ],
        )

    def _subscription_price(self, spec: _ServiceSpec, region_id: str) -> Decimal:
        """A fixed synthetic fee per provider/service/region, between USD 20 and 800."""
        key = _stable_id(
            "", [self.profile.provider_name, spec.name, region_id, "subscription"]
        )
        return Decimal(2000 + int(key[:8], 16) % 78001) / Decimal(100)

    def _set_currency(
        self,
        row: dict[str, str],
        pricing_currency: str,
        list_unit: Decimal,
        contracted_unit: Decimal,
        effective_cost: Decimal,
    ) -> None:
        row["PricingCurrency"] = pricing_currency
        fx = _EUR_PER_USD if pricing_currency == "EUR" else Decimal("1")
        row["PricingCurrencyListUnitPrice"] = _s(_q(list_unit * fx, _PRICE_Q))
        row["PricingCurrencyContractedUnitPrice"] = _s(
            _q(contracted_unit * fx, _PRICE_Q)
        )
        row["PricingCurrencyEffectiveCost"] = _s_cost(effective_cost * fx)
        self._set_sku_ids(row)

    def _usage_row(self, rng: random.Random, i: int) -> dict[str, str]:
        spec = rng.choice(self.profile.services)
        region_id, region_name, azs = rng.choice(self.profile.regions)
        row, ctx = self._base_row(rng)
        start, end = _period(i, spec.granularity)
        row["ChargePeriodStart"], row["ChargePeriodEnd"] = (start, end)
        self._set_service(row, spec)
        resource_name = f"{spec.name_prefix}{_hexid(rng, self.profile.resource_width)}"
        self._set_resource_sku(
            rng, row, spec, ctx, region_id, region_name, resource_name
        )
        if spec.zonal:
            row["AvailabilityZone"] = rng.choice(azs)
        quantity = _q(
            Decimal(rng.uniform(float(spec.qty_low), float(spec.qty_high))), _QTY_Q
        )
        list_unit = _q(spec.unit_price_usd, _PRICE_Q)
        has_contract = self.adapter.select_contract(rng)
        contracted_unit = (
            _q(list_unit * _PRIVATE_RATE, _PRICE_Q) if has_contract else list_unit
        )
        list_cost = list_unit * quantity
        contracted_cost = contracted_unit * quantity
        row["ChargeCategory"] = "Usage"
        row["ChargeFrequency"] = "Usage-Based"
        row["ChargeDescription"] = spec.description
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
        self.adapter.apply_negotiated(
            row, self.profile, has_contract, spec, quantity, contracted_cost
        )
        self._set_currency(
            row,
            "EUR" if rng.random() < 0.1 else "USD",
            list_unit,
            contracted_unit,
            contracted_cost,
        )
        return row

    def _standalone_purchase_row(self, rng: random.Random, i: int) -> dict[str, str]:
        spec = rng.choice(self.profile.services)
        region_id, region_name, _ = rng.choice(self.profile.regions)
        row, ctx = self._base_row(rng)
        row["ChargePeriodStart"], row["ChargePeriodEnd"] = _period(i, "daily")
        self._set_service(row, spec)
        resource_name = f"{spec.name_prefix}{_hexid(rng, self.profile.resource_width)}"
        self._set_resource_sku(
            rng, row, spec, ctx, region_id, region_name, resource_name
        )
        amount = self._subscription_price(spec, region_id)
        row["SkuMeter"] = "Subscription"
        row["SkuPriceDetails"] = json.dumps({"x_ChargeType": "SubscriptionFee"})
        row["ChargeCategory"] = "Purchase"
        row["ChargeFrequency"] = "Recurring"
        row["ChargeDescription"] = f"{spec.name} subscription fee"
        row["PricingCategory"] = "Standard"
        row["BilledCost"] = _s(amount)
        row["EffectiveCost"] = _s_cost(amount)
        row["ListCost"] = _s(amount)
        row["ContractedCost"] = _s(amount)
        row["ListUnitPrice"] = _s(amount)
        row["ContractedUnitPrice"] = _s(amount)
        row["PricingQuantity"] = "1"
        row["PricingUnit"] = "Units"
        self._set_currency(row, "USD", amount, amount, amount)
        return row

    def _tax_row(self, source: dict[str, str], source_number: int) -> dict[str, str]:
        """Synthetic 10% tax on one previously emitted, otherwise untaxed usage row.

        source_number counts data records from one (excluding the CSV header).
        This pedagogical rate does not represent any jurisdiction's tax rules.
        """
        row = {name: "" for name in self.adapter.columns}
        for name in (
            *_BILLING_IDENTITY_KEYS,
            "BillingPeriodStart",
            "BillingPeriodEnd",
            "ChargePeriodStart",
            "ChargePeriodEnd",
            "BillingCurrency",
            "PricingCurrency",
            "ProviderName",
            "PublisherName",
            "InvoiceIssuerName",
            "ServiceName",
            "ServiceCategory",
            "ServiceSubcategory",
            "Tags",
            "ServiceProviderName",
            "HostProviderName",
        ):
            if name in row:
                row[name] = source[name]
        row["ChargeCategory"] = "Tax"
        row["ChargeFrequency"] = "One-Time"
        row["ChargeDescription"] = (
            f"Synthetic tax 10% on usage record {source_number}: {source['ServiceName']}"
        )
        for name in (
            "BilledCost",
            "EffectiveCost",
            "ListCost",
            "ContractedCost",
            "PricingCurrencyEffectiveCost",
        ):
            row[name] = _s_cost(Decimal(source[name]) * Decimal("0.1"))
        return row

    def _credit_row(self, rng: random.Random, i: int) -> dict[str, str]:
        spec = rng.choice(self.profile.services)
        row, _ = self._base_row(rng)
        row["ChargePeriodStart"], row["ChargePeriodEnd"] = _period(i, "daily")
        self._set_service(row, spec)
        negative = _s(-_q(Decimal(rng.uniform(1.0, 100.0)), _COST_Q))
        row["ChargeCategory"] = "Credit"
        row["ChargeFrequency"] = "One-Time"
        row["ChargeDescription"] = f"Credit for {spec.name}"
        row["BilledCost"] = negative
        row["EffectiveCost"] = negative
        row["ListCost"] = negative
        row["ContractedCost"] = negative
        row["PricingCurrency"] = "USD"
        row["PricingCurrencyEffectiveCost"] = negative
        return row

    def _commitment_group(
        self, rng: random.Random, i0: int, remaining: int, registry=None
    ) -> list[dict[str, str]]:
        """One commitment discount, modelled over the charge periods the fixture holds.

        FOCUS amortises a commitment discount evenly over each charge period of its term,
        use-it-or-lose-it: what a period does not consume is wasted rather than carried
        forward. A fixture covering a slice of the term therefore carries, for each period
        it holds, the recurring purchase row and either the usage that drew the commitment
        down (``Used``) or the amount that went to waste (``Unused``). Both per period and
        over the group, ``sum(EffectiveCost where Usage) == sum(BilledCost where Purchase)``.
        """
        spec = self.profile.services[0]
        region_id, region_name, azs = rng.choice(self.profile.regions)
        zone = rng.choice(azs)
        spend_based = rng.random() < 0.6
        index = 0 if spend_based else 1
        commit_kind = self.profile.commitment_kinds[index]
        commit_type = self.profile.commitment_types[index]
        commit_name = self.profile.commitment_names[index]
        commit_category = "Spend" if spend_based else "Usage"
        commit_unit = "USD" if spend_based else "Hours"
        list_unit = _q(spec.unit_price_usd, _PRICE_Q)
        contracted_unit = _q(list_unit * _PRIVATE_RATE, _PRICE_Q)
        commit_unit_rate = _q(list_unit * _COMMIT_RATE, _PRICE_Q)
        commit_rate = commit_unit_rate * _FLEET_SIZE
        n_usage = rng.randint(5, 9)
        n_unused = rng.randint(1, 3)
        n_periods = n_usage + n_unused
        if 2 * n_periods > remaining:
            return []
        first, ctx = self._base_row(rng)
        commit_id = self.profile.commitment_id(
            rng, region_id, ctx, commit_kind, spend_based
        )
        commit_resource_name = (
            f"{commit_kind}-{_hexid(rng, self.profile.commitment_name_width)}"
        )
        commit_sku_details = self.profile.commitment_details
        if spend_based:
            commit_price_unit = Decimal("1")
            commit_pricing_qty = commit_rate
            commit_pricing_unit = "USD"
            commit_drawdown = _s_cost(commit_rate)
        else:
            commit_price_unit = commit_unit_rate
            commit_pricing_qty = _FLEET_SIZE
            commit_pricing_unit = "Hours"
            commit_drawdown = _s_cost(_FLEET_SIZE)
        billing_identity = {key: first[key] for key in _BILLING_IDENTITY_KEYS}
        contract_id = self.adapter.record_commitment(
            registry,
            commit_id,
            commit_type,
            commit_category,
            commit_rate,
            spend_based,
            commit_unit,
            commit_name,
        )

        def _commitment_columns(row: dict[str, str], status: str | None) -> None:
            row["CommitmentDiscountId"] = commit_id
            row["CommitmentDiscountName"] = commit_name
            row["CommitmentDiscountCategory"] = commit_category
            row["CommitmentDiscountType"] = commit_type
            row["CommitmentDiscountQuantity"] = commit_drawdown
            row["CommitmentDiscountUnit"] = commit_unit
            if status is not None:
                row["CommitmentDiscountStatus"] = status

        def _commitment_resource(row: dict[str, str]) -> None:
            row["ResourceId"] = commit_id
            row["ResourceName"] = commit_resource_name
            row["ResourceType"] = commit_type
            row["RegionId"] = region_id
            row["RegionName"] = region_name
            row["SkuMeter"] = "Commitment"
            row["SkuPriceDetails"] = commit_sku_details

        fleet_name = _stable_id(
            "fleet", [self.profile.provider_name, ctx["sub_id"], region_id, commit_id]
        )
        fleet_id = f"urn:focus-sample:{self.profile.key}:{region_id}:{ctx['sub_id']}:compute-fleet:{fleet_name}"
        rows: list[dict[str, str]] = []
        for k in range(n_periods):
            start, end = _period(i0 + k, "hourly")
            purchase = first if k == 0 else self._base_row(rng)[0]
            purchase.update(billing_identity)
            purchase["ChargePeriodStart"], purchase["ChargePeriodEnd"] = (start, end)
            self._set_service(purchase, spec)
            _commitment_resource(purchase)
            purchase["ChargeCategory"] = "Purchase"
            purchase["ChargeFrequency"] = "Recurring"
            purchase["ChargeDescription"] = (
                f"{commit_type} commitment, amortised for the charge period"
            )
            purchase["PricingCategory"] = "Standard"
            purchase["BilledCost"] = _s_cost(commit_rate)
            purchase["EffectiveCost"] = "0"
            purchase["ListCost"] = _s_cost(commit_rate)
            purchase["ContractedCost"] = _s_cost(commit_rate)
            purchase["ListUnitPrice"] = _s(commit_price_unit)
            purchase["ContractedUnitPrice"] = _s(commit_price_unit)
            purchase["PricingQuantity"] = _s_cost(commit_pricing_qty)
            purchase["PricingUnit"] = commit_pricing_unit
            _commitment_columns(purchase, None)
            self._set_currency(
                purchase, "USD", commit_price_unit, commit_price_unit, Decimal("0")
            )
            rows.append(purchase)
            usage, _ = self._base_row(rng)
            usage.update(billing_identity)
            usage["ChargePeriodStart"], usage["ChargePeriodEnd"] = (start, end)
            self._set_service(usage, spec)
            usage["ChargeCategory"] = "Usage"
            usage["ChargeFrequency"] = "Usage-Based"
            usage["PricingCategory"] = "Committed"
            usage["BilledCost"] = "0"
            if k < n_usage:
                used_qty = _FLEET_SIZE
                resource_name = f"{spec.name_prefix}{k:04d}{_hexid(rng, self.profile.committed_width)}"
                usage["ResourceId"] = self.profile.resource_id(
                    rng, spec, region_id, ctx, resource_name
                )
                usage["ResourceName"] = resource_name
                usage["ResourceType"] = spec.resource_type
                usage["RegionId"] = region_id
                usage["RegionName"] = region_name
                usage["AvailabilityZone"] = zone
                usage["SkuMeter"] = spec.sku_meter
                usage["SkuPriceDetails"] = json.dumps(
                    dict(spec.sku_details), separators=(",", ":")
                )
                usage["ResourceId"] = fleet_id
                usage["ResourceName"] = fleet_name
                usage["ResourceType"] = "Compute Fleet"
                tags = json.loads(usage["Tags"])
                tags["SyntheticFleetSize"] = "500"
                usage["Tags"] = json.dumps(tags, separators=(",", ":"))
                usage["ChargeDescription"] = (
                    f"{spec.name} committed usage of 500 machine-equivalents"
                )
                usage["EffectiveCost"] = _s_cost(commit_unit_rate * used_qty)
                usage["ListCost"] = _s_cost(list_unit * used_qty)
                usage["ContractedCost"] = _s_cost(contracted_unit * used_qty)
                usage["ListUnitPrice"] = _s(list_unit)
                usage["ContractedUnitPrice"] = _s(contracted_unit)
                usage["PricingQuantity"] = _s_cost(used_qty)
                usage["PricingUnit"] = "Hours"
                usage["ConsumedQuantity"] = _s_cost(used_qty)
                usage["ConsumedUnit"] = "Hours"
                _commitment_columns(usage, "Used")
                self._set_currency(
                    usage,
                    "USD",
                    list_unit,
                    contracted_unit,
                    commit_unit_rate * used_qty,
                )
            else:
                _commitment_resource(usage)
                usage["ChargeDescription"] = f"{commit_type} unused commitment"
                usage["EffectiveCost"] = _s_cost(commit_rate)
                usage["ListCost"] = _s_cost(commit_rate)
                usage["ContractedCost"] = _s_cost(commit_rate)
                usage["ListUnitPrice"] = _s(commit_price_unit)
                usage["ContractedUnitPrice"] = _s(commit_price_unit)
                usage["PricingQuantity"] = _s_cost(commit_pricing_qty)
                usage["PricingUnit"] = commit_pricing_unit
                _commitment_columns(usage, "Unused")
                self._set_currency(
                    usage, "USD", commit_price_unit, commit_price_unit, commit_rate
                )
            self.adapter.apply_commitment(
                usage,
                contract_id,
                commit_id,
                commit_rate,
                spend_based,
                commit_pricing_qty,
                commit_unit,
            )
            rows.append(usage)
        if len(rows) > remaining:
            raise ValueError("commitment group exceeded its row budget")
        return rows

    def generate_rows(
        self,
        rows: int = DEFAULT_ROWS,
        seed: int = None,
        *,
        include_credits: bool = False,
        registry=None,
    ) -> list[dict[str, str]]:
        """Return ``rows`` synthetic FOCUS 1.2 records as ordered string dicts."""
        if seed is None:
            seed = self.adapter.default_seed
        if rows < 1:
            raise ValueError("rows must be >= 1")
        rng = random.Random(seed)
        registry = (
            self.adapter.new_registry(self.profile) if registry is None else registry
        )
        out: list[dict[str, str]] = []
        untaxed: list[int] = []
        while len(out) < rows:
            i = len(out)
            remaining = rows - i
            roll = rng.random()
            if include_credits and roll < 0.05:
                out.append(self._credit_row(rng, i))
            elif roll < 0.12:
                if untaxed:
                    source_index = untaxed.pop(rng.randrange(len(untaxed)))
                    out.append(self._tax_row(out[source_index], source_index + 1))
                else:
                    out.append(self._usage_row(rng, i))
            elif roll < 0.2:
                out.append(self._standalone_purchase_row(rng, i))
            elif roll < self.adapter.split_threshold:
                out.append(self.adapter.split_row(self, rng, i))
            elif roll < self.adapter.commitment_threshold:
                group = self._commitment_group(rng, i, remaining, registry)
                out.extend(group or [self._usage_row(rng, i)])
            else:
                out.append(self._usage_row(rng, i))
            untaxed.extend(
                (
                    index
                    for index in range(i, len(out))
                    if out[index]["ChargeCategory"] == "Usage"
                    and out[index]["PricingCategory"] == "Standard"
                )
            )
        assert len(out) == rows, "generator exceeded the row budget"
        return out

    def generate_csv_bytes(
        self,
        rows: int = DEFAULT_ROWS,
        seed: int = None,
        *,
        include_credits: bool = False,
    ) -> bytes:
        """Serialise the generated rows to deterministic UTF-8 CSV bytes (LF line endings)."""
        if seed is None:
            seed = self.adapter.default_seed
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer, fieldnames=list(self.adapter.columns), lineterminator="\n"
        )
        writer.writeheader()
        for record in self.generate_rows(rows, seed, include_credits=include_credits):
            writer.writerow(record)
        return buffer.getvalue().encode("utf-8")
