"""Immutable provider inputs. Callbacks format IDs and own their historical RNG draws."""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable
from types import MappingProxyType


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    category: str
    subcategory: str
    resource_type: str
    id_parts: tuple[str, ...]
    sku_meter: str
    pricing_unit: str
    description: str
    unit_price_usd: Decimal
    qty_low: Decimal
    qty_high: Decimal
    name_prefix: str
    granularity: str
    zonal: bool
    commitment_eligible: bool
    sku_details: dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(
            self, "sku_details", MappingProxyType(dict(self.sku_details))
        )


@dataclass(frozen=True)
class ProviderProfile:
    key: str
    label: str
    provider_name: str
    publisher_name: str
    invoice_issuer: str
    billing_type: str
    sub_type: str
    invoice_id: Callable[[str], str]
    tag_keys: tuple[str, str, str]
    services: tuple[ServiceSpec, ...]
    regions: tuple
    billing_accounts: tuple
    sub_accounts: tuple
    resource_id: Callable
    resource_width: int
    committed_width: int
    commitment_kinds: tuple[str, str]
    commitment_types: tuple[str, str]
    commitment_names: tuple[str, str]
    commitment_id: Callable
    commitment_name_width: int
    commitment_details: str
    allocation_id: Callable
    allocation_description: str
    negotiated_terms: tuple = ()
    negotiated_contract_id: str = ""
