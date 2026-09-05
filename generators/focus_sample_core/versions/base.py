"""FOCUS 1.2 adapter and the small extension interface for later versions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VersionAdapter:
    version: str
    columns: tuple[str, ...]
    default_seed: int
    split_threshold: float = 0.0
    commitment_threshold: float = 0.23
    contract_columns: tuple[str, ...] | None = None

    def fill_identity(self, row, profile):
        pass

    def select_contract(self, rng):
        return (
            True  # 1.2 retains its reviewed negotiated baseline, without an extra draw.
        )

    def apply_negotiated(self, row, profile, selected, spec, quantity, cost):
        pass

    def new_registry(self, profile):
        return None

    def record_commitment(
        self, registry, commit_id, kind, category, rate, spend, unit, name
    ):
        return None

    def apply_commitment(
        self, row, contract_id, commit_id, rate, spend, quantity, unit
    ):
        pass

    def split_row(self, engine, rng, index):
        raise ValueError("Split allocation is not a scenario of this version")
