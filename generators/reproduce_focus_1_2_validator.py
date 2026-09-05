"""Extract single-record, synthetic reproductions of specific validator defects.

These are diagnostic snippets, not complete billing-period conformance fixtures.
--run records the full official report and asserts only the named target failures.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import validate_focus_1_2_samples as evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=evidence.EVIDENCE / "local" / "reproductions")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    output = args.out.resolve(); output.mkdir(parents=True, exist_ok=True)
    source = evidence.DATA / "focus_sample_costandusage_aws_1000.csv"
    with source.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    prefix = "CAU-" if "1.2" == "1.3" else ""
    cases = [("period-subscription", next((i, r) for i, r in enumerate(rows, 1)
              if r["ChargeCategory"] == "Purchase" and not r["CommitmentDiscountId"]), [prefix + "EffectiveCost-C-005-C"])]
    if "1.2" == "1.3":
        cases += [("spend-optional-properties", next((i, r) for i, r in enumerate(rows, 1)
                   if r["ContractApplied"] and "ContractCommitmentAppliedQuantity" not in r["ContractApplied"]),
                   ["CAU-ContractAppliedObject-O-007-M", "CAU-ContractAppliedObject-O-039-C"]),
                  ("usage-element-conditions", next((i, r) for i, r in enumerate(rows, 1)
                   if r["ContractApplied"] and "ContractCommitmentAppliedQuantity" in r["ContractApplied"]),
                   ["CAU-ContractAppliedObject-O-039-C", "CAU-ContractAppliedObject-O-065-C"])]
    runtime = json.loads((evidence.EVIDENCE / "runtime.json").read_text(encoding="utf-8"))
    if args.run:
        import focus_validator
        import importlib.metadata
        if importlib.metadata.version("focus-validator") != "2.2.1":
            raise ValueError("Use focus-validator 2.2.1")
        package = Path(focus_validator.__file__).resolve().parent
        model_path = package / "rules/model-1.2.0.1.json"
        if (evidence.digest(model_path) != runtime["model_sha256"]
            or evidence.digest(package / "rules/currency_codes.csv") != runtime["currency_codes_sha256"]):
            raise ValueError("Unreviewed validator/model resources")
        model = json.loads(model_path.read_text(encoding="utf-8"))
    for name, (number, row), targets in cases:
        file = output / (name + ".csv")
        with file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row), lineterminator="\n")
            writer.writeheader(); writer.writerow(row)
        meta = dict(source=source.name, source_data_record=number, source_sha256=evidence.digest(source),
                    input_sha256=evidence.digest(file), target_rules=targets, model=runtime["model"],
                    model_sha256=runtime["model_sha256"], validator="2.2.1")
        if args.run:
            command = [sys.executable, "-m", "focus_validator.main", "--data-file", str(file),
                       "--validate-version", "1.2.0.1", "--focus-dataset", "CostAndUsage",
                       "--applicability-criteria", "ALL", "--show-violations", "--block-download"]
            result = subprocess.run(command, cwd=package.parent, capture_output=True,
                                    env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))
            raw = result.stdout + result.stderr
            (output / (name + ".log")).write_bytes(raw)
            if result.returncode:
                raise RuntimeError(f"Validator exited {result.returncode}")
            report = evidence.parse_report(raw.decode("utf-8"))
            if not all(report["failures"].get(key, 0) > 0 for key in targets):
                raise ValueError(f"Target behavior changed: {name}: {report['failures']}")
            meta.update(observed_target_failures={key: report["failures"][key] for key in targets},
                        model_rules={key: model["ModelRules"][key] for key in targets},
                        command="focus-validator --data-file " + name + ".csv --validate-version 1.2.0.1 --focus-dataset CostAndUsage --applicability-criteria ALL --show-violations --block-download")
        (output / (name + ".json")).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(name, "reproduced" if args.run else "extracted", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
