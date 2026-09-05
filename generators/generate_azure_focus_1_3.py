"""AZURE FOCUS 1.3 entry point; shared logic lives in focus_sample_core."""
from __future__ import annotations
from pathlib import Path
from focus_sample_core.engine import Engine
from focus_sample_core.cli import main as run_cli
from focus_sample_core.profiles.azure_contracts import PROFILE
from focus_sample_core.versions.v1_3 import ADAPTER
from focus_sample_core.values import (
    PRICING_CATEGORIES, FOCUS_SKU_PRICE_KEYS, _decimal_json, _s_decimal,
)

DEFAULT_ROWS = 1000
DEFAULT_SEED = 1302
DEFAULT_OUT = Path("FOCUS-1.3/focus_sample_costandusage_azure_1000.csv")
COLUMNS = ADAPTER.columns
PROVIDER_NAME = PROFILE.provider_name
PUBLISHER_NAME = PROFILE.publisher_name
INVOICE_ISSUER_NAME = PROFILE.invoice_issuer
ALLOWED_SUBCATEGORIES = frozenset(s.subcategory for s in PROFILE.services)
ENGINE = Engine(PROFILE, ADAPTER)

# Compatibility handles for the existing independent regression tests.
_tax_row = ENGINE._tax_row
_commitment_group = ENGINE._commitment_group

def generate_rows(rows: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED, *, include_credits: bool = False, registry=None):
    return ENGINE.generate_rows(rows, seed, include_credits=include_credits, registry=registry)

def generate_csv_bytes(rows: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED, *, include_credits: bool = False) -> bytes:
    return ENGINE.generate_csv_bytes(rows, seed, include_credits=include_credits)

from focus_sample_core.versions.v1_3 import (
    _contract_applied, _ContractRegistry as ContractRegistry,
    generate_contract_commitment_rows as contract_rows,
    generate_contract_commitment_csv_bytes as contract_csv,
)
CONTRACT_COMMITMENT_COLUMNS = ADAPTER.contract_columns
DEFAULT_COMMITMENT_OUT = Path("FOCUS-1.3/focus_sample_contractcommitment_azure.csv")

def _ContractRegistry():
    return ContractRegistry(PROFILE)

def generate_contract_commitment_rows(rows=DEFAULT_ROWS, seed=DEFAULT_SEED):
    return contract_rows(ENGINE, rows, seed)

def generate_contract_commitment_csv_bytes(rows=DEFAULT_ROWS, seed=DEFAULT_SEED):
    return contract_csv(ENGINE, rows, seed)

def main(argv: list[str] | None = None) -> int:
    return run_cli(ENGINE, argv, generate_contract_commitment_csv_bytes)

if __name__ == "__main__":
    raise SystemExit(main())
