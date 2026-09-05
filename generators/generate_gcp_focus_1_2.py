"""GCP FOCUS 1.2 entry point; shared logic lives in focus_sample_core."""
from __future__ import annotations
from pathlib import Path
from focus_sample_core.engine import Engine
from focus_sample_core.cli import main as run_cli
from focus_sample_core.profiles.gcp import PROFILE
from focus_sample_core.versions.v1_2 import ADAPTER
from focus_sample_core.values import (
    PRICING_CATEGORIES, FOCUS_SKU_PRICE_KEYS, _decimal_json, _s_decimal,
)

DEFAULT_ROWS = 1000
DEFAULT_SEED = 1202
DEFAULT_OUT = Path("FOCUS-1.2/focus_sample_costandusage_gcp_1000.csv")
COLUMNS = ADAPTER.columns
PROVIDER_NAME = PROFILE.provider_name
PUBLISHER_NAME = PROFILE.publisher_name
INVOICE_ISSUER_NAME = PROFILE.invoice_issuer
ALLOWED_SUBCATEGORIES = frozenset(s.subcategory for s in PROFILE.services)
ENGINE = Engine(PROFILE, ADAPTER)

# Compatibility handles for the existing independent regression tests.
_tax_row = ENGINE._tax_row
_commitment_group = ENGINE._commitment_group

def generate_rows(rows: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED, *, include_credits: bool = False):
    return ENGINE.generate_rows(rows, seed, include_credits=include_credits)

def generate_csv_bytes(rows: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED, *, include_credits: bool = False) -> bytes:
    return ENGINE.generate_csv_bytes(rows, seed, include_credits=include_credits)


def main(argv: list[str] | None = None) -> int:
    return run_cli(ENGINE, argv)

if __name__ == "__main__":
    raise SystemExit(main())
