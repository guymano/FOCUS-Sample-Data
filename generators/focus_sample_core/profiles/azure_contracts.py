"""Reviewed FOCUS 1.3 negotiated terms for this provider."""

from dataclasses import replace
from decimal import Decimal
from .azure import PROFILE as BASE

_NEGOTIATED_CONTRACT_ID = "CONTRACT-MACC-2026-0001"
_NEGOTIATED_TERMS: tuple[
    tuple[str, str, str, Decimal, Decimal | None, str | None, str], ...
] = (
    (
        "CC-MACC-SPEND-0001",
        "Microsoft Azure Consumption Commitment",
        "Spend",
        Decimal("250000"),
        None,
        None,
        "Annual MACC minimum spend",
    ),
    (
        "CC-MACC-STORAGE-0002",
        "Negotiated Storage Rate Card",
        "Spend",
        Decimal("48000"),
        None,
        None,
        "Negotiated Azure Storage rate card",
    ),
    (
        "CC-MACC-COMPUTE-0003",
        "Compute Usage Commitment",
        "Usage",
        Decimal("180000"),
        Decimal("2000000"),
        "Hours",
        "Committed annual Virtual Machines compute hours",
    ),
)
PROFILE = replace(
    BASE,
    negotiated_terms=_NEGOTIATED_TERMS,
    negotiated_contract_id=_NEGOTIATED_CONTRACT_ID,
)
