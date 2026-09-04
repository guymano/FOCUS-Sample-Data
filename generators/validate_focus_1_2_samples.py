"""Run the unmodified official validator and reject unreviewed results.

Requires the optional validation/requirements.txt environment. Generators and their
regression tests still use only the standard library. --check-existing verifies the
committed reports and CSV hashes without importing or executing focus-validator.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import check_focus_1_2_samples as audit

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "FOCUS-1.2"
EVIDENCE = DATA / "validation"


def check_report(text: str, expected: dict) -> list[str]:
    totals = re.search(r"Total: (\d+) \| Pass: (\d+) \| Fail: (\d+) \| Skipped: (\d+)", text)
    if not totals or "Traceback (most recent call last)" in text:
        return ["validator did not complete"]
    total, passed, failed, skipped_count = map(int, totals.groups())
    failures = {m[1]: int(m[2]) for m in re.finditer(r"^\S+ ([\w-]+): FAIL  \(violations=(\d+)", text, re.M)}
    skipped = re.findall(r"^\S+ ([\w-]+): SKIPPED ", text, re.M)
    errors = []
    if total != passed + failed + skipped_count or failed != len(failures) or skipped_count != len(skipped):
        errors.append("report totals disagree with individual rules")
    if failures != expected["failures"]:
        errors.append("failing rules or violation counts differ from the reviewed evidence")
    if set(skipped) != set(expected["skipped_rules"]):
        errors.append("skipped rules differ from the reviewed evidence")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-existing", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE / "local")
    args = parser.parse_args(argv)
    expected = json.loads((EVIDENCE / "expected.json").read_text(encoding="utf-8"))
    runtime = json.loads((EVIDENCE / "runtime.json").read_text(encoding="utf-8"))
    # Run the independent fixture audit before interpreting validator failures.
    for provider in audit.PROVIDERS:
        with (DATA / f"focus_sample_costandusage_{provider}_1000.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        contracts = None
        contract_path = DATA / f"focus_sample_contractcommitment_{provider}.csv"
        if contract_path.exists():
            with contract_path.open(newline="", encoding="utf-8") as f:
                contracts = list(csv.DictReader(f))
        errors = audit.audit_rows(rows, provider)
        if errors:
            print("Independent data audit failed:", "\n".join(errors[:10]))
            return 1
    if not args.check_existing:
        import focus_validator
        if importlib.metadata.version("focus-validator") != runtime["validator"]:
            raise RuntimeError("Use the recorded focus-validator version")
        package = Path(focus_validator.__file__).resolve().parent
        for name, key in (("model-1.2.0.1.json", "model_sha256"), ("currency_codes.csv", "currency_codes_sha256")):
            if hashlib.sha256((package / "rules" / name).read_bytes()).hexdigest() != runtime[key]:
                raise RuntimeError(f"Unreviewed validator resource: {name}")
        args.output_dir.mkdir(parents=True, exist_ok=True)
    failed_files = 0
    for name, snapshot in sorted(expected.items()):
        source = DATA / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != snapshot["data_sha256"]:
            print(f"FAIL {name}: CSV differs from reviewed evidence; regenerate and revalidate")
            failed_files += 1
            continue
        if args.check_existing:
            text = (EVIDENCE / "after" / (source.stem + ".log")).read_text(encoding="utf-8")
        else:
            dataset = "ContractCommitment" if "contractcommitment" in name else "CostAndUsage"
            command = [sys.executable, "-m", "focus_validator.main", "--data-file", str(source),
                       "--validate-version", "1.2.0.1", "--focus-dataset", dataset,
                       "--applicability-criteria", "ALL", "--show-violations", "--block-download"]
            # 2.2.1 uses a relative currency_codes.csv path. Do not patch its implementation.
            result = subprocess.run(command, cwd=package.parent, capture_output=True,
                                    env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))
            text = result.stdout.decode("utf-8") + result.stderr.decode("utf-8")
            (args.output_dir / (source.stem + ".log")).write_text(text, encoding="utf-8", newline="\n")
            if result.returncode:
                print(f"FAIL {name}: validator exited {result.returncode}")
                failed_files += 1
                continue
        errors = check_report(text, snapshot)
        if errors:
            print(f"FAIL {name}: {'; '.join(errors)}")
            failed_files += 1
        else:
            count = len(snapshot["failures"])
            print(f"{name}: {count} reviewed validator failures; {len(snapshot['skipped_rules'])} rules skipped")
    if not failed_files:
        print("Evidence matches. Reviewed artifacts and skipped rules are NOT conformance passes.")
    return int(bool(failed_files))


if __name__ == "__main__":
    raise SystemExit(main())
