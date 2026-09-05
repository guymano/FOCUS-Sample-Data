"""Reviewed FOCUS 1.3 negotiated terms for this provider."""

from dataclasses import replace
from decimal import Decimal
from .aws import PROFILE as BASE

_NEGOTIATED_CONTRACT_ID = "CONTRACT-EA-2026-0001"
_NEGOTIATED_TERMS: tuple[
    tuple[str, str, str, Decimal, Decimal | None, str | None, str], ...
] = (
    (
        "CC-EA-SPEND-0001",
        "Enterprise Agreement Minimum Spend",
        "Spend",
        Decimal("250000"),
        None,
        None,
        "Annual minimum spend committed under the enterprise agreement",
    ),
    (
        "CC-EA-STORAGE-0002",
        "Negotiated Storage Rate Card",
        "Spend",
        Decimal("48000"),
        None,
        None,
        "Negotiated S3 storage rate card",
    ),
    (
        "CC-EA-COMPUTE-0003",
        "Compute Usage Commitment",
        "Usage",
        Decimal("180000"),
        Decimal("2000000"),
        "Hours",
        "Committed annual EC2 compute hours",
    ),
)
PROFILE = replace(
    BASE,
    negotiated_terms=_NEGOTIATED_TERMS,
    negotiated_contract_id=_NEGOTIATED_CONTRACT_ID,
)
