"""Exact arithmetic, stable identifiers and deterministic fixture constants."""

from __future__ import annotations
import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

PRICING_CATEGORIES: tuple[str, ...] = ("Standard", "Dynamic", "Committed", "Other")

FOCUS_SKU_PRICE_KEYS: frozenset[str] = frozenset(
    {
        "StorageClass",
        "Redundancy",
        "CoreCount",
        "MemorySize",
        "InstanceType",
        "InstanceSeries",
        "OperatingSystem",
        "DiskType",
        "DiskSpace",
        "DiskMaxIops",
        "GpuCount",
        "NetworkMaxIops",
        "NetworkMaxThroughput",
    }
)

_BILLING_IDENTITY_KEYS: tuple[str, ...] = (
    "BillingAccountId",
    "BillingAccountName",
    "BillingAccountType",
    "SubAccountId",
    "SubAccountName",
    "SubAccountType",
    "InvoiceId",
)

_BILLING_START = datetime(2026, 5, 1, tzinfo=UTC)

_BILLING_END = datetime(2026, 6, 1, tzinfo=UTC)

_PERIOD_DAYS = 28

_PERIOD_HOURS = _PERIOD_DAYS * 24

_COST_Q = Decimal("0.000001")

_PRICE_Q = Decimal("0.0000000001")

_QTY_Q = Decimal("0.0001")

_EUR_PER_USD = Decimal("0.92")

_COMMIT_RATE = Decimal("0.667")

_PRIVATE_RATE = Decimal("0.90")

_FLEET_SIZE = Decimal("500")

_COMMIT_TERM_HOURS = Decimal("8760")

_ENVIRONMENTS = ("prod", "staging", "dev")

_COST_CENTERS = ("cc-1042", "cc-2087", "cc-3110")

_OWNERS = ("team-platform", "team-data", "team-payments")


def _q(value: Decimal, quant: Decimal) -> Decimal:
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def _s(value: Decimal) -> str:
    return format(value, "f")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _hexid(rng: random.Random, width: int) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(width))


def _period(i: int, granularity: str) -> tuple[str, str]:
    if granularity == "hourly":
        start = _BILLING_START + timedelta(hours=i % _PERIOD_HOURS)
        return _iso(start), _iso(start + timedelta(hours=1))
    if granularity == "daily":
        start = _BILLING_START + timedelta(days=i % _PERIOD_DAYS)
        return _iso(start), _iso(start + timedelta(days=1))
    return _iso(_BILLING_START), _iso(_BILLING_END)


def _trim(value: Decimal) -> Decimal:
    """Drop trailing zeros without falling back to exponent notation."""
    trimmed = value.normalize()
    if trimmed == 0:
        return Decimal(0)
    _, _, exponent = trimmed.as_tuple()
    return trimmed.quantize(Decimal(1)) if exponent > 0 else trimmed


def _s_cost(value: Decimal) -> str:
    """Serialise a cost column.

    FOCUS 1.3 requires ``ListCost`` to *equal* ``ListUnitPrice`` x ``PricingQuantity``
    (same for ``ContractedCost``), with no rounding tolerance, so derived costs are
    exact products that are never re-quantised. Only trailing zeros are dropped.
    """
    return format(_trim(value), "f")


def _stable_id(prefix: str, values: object) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return prefix + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _decimal_json(value: object) -> str:
    """Emit exact finite Decimal JSON numbers without a binary-float round trip."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("JSON decimal must be finite")
        return format(value, "f")
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        return (
            "{"
            + ",".join(
                json.dumps(key) + ":" + _decimal_json(item)
                for key, item in value.items()
            )
            + "}"
        )
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_decimal_json(item) for item in value) + "]"
    if value is None or isinstance(value, (str, bool, int)):
        return json.dumps(value, ensure_ascii=True, allow_nan=False)
    raise TypeError(f"Unsupported exact JSON value: {type(value).__name__}")


def _s_decimal(value: Decimal) -> str:
    text = _s_cost(value)
    return text if "." in text else text + ".0"
