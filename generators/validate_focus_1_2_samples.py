"""Check or record unmodified official-validator evidence; recording never accepts it.

--record DIR writes candidate reports, manifests and tables for review. It does not
replace the committed expectations. Default runs compare with those expectations;
--check-existing checks saved evidence without importing the optional validator.
"""
import argparse
from collections import Counter
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


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_report(text):
    totals = re.findall(r"Total: (\d+) \| Pass: (\d+) \| Fail: (\d+) \| Skipped: (\d+)", text)
    if len(totals) != 1 or "Traceback (most recent call last)" in text:
        raise ValueError("validator did not produce exactly one complete report")
    total, passed, failed, skipped = map(int, totals[0])
    entries = re.findall(r"^\S+ ([\w-]+): (PASS|FAIL|SKIPPED) +\(violations=(\d+)", text, re.M)
    rules = {key: status for key, status, count in entries}
    counts = Counter(status for key, status, count in entries)
    if (len(rules) != len(entries) or total != len(entries) or total != passed + failed + skipped
        or [counts[s] for s in ("PASS", "FAIL", "SKIPPED")] != [passed, failed, skipped]):
        raise ValueError("missing/duplicate rule or inconsistent report totals")
    return {"total": total, "passed": passed, "failed": failed, "skipped": skipped,
            "rules": rules, "failures": {key: int(count) for key, status, count in entries if status == "FAIL"},
            "skipped_rules": [key for key, status, count in entries if status == "SKIPPED"]}


def check_report(text, expected):
    try:
        result = parse_report(text)
    except ValueError as exc:
        return [str(exc)]
    errors = []
    if result["rules"] != expected["rules"]:
        errors.append("complete rule inventory or states differ from reviewed evidence")
    if result["failures"] != expected["failures"]:
        errors.append("failing rule counts differ from reviewed evidence")
    if result["skipped_rules"] != expected["skipped_rules"]:
        errors.append("skipped rules differ from reviewed evidence")
    return errors


def snapshot_errors(source, expected):
    provider = re.search(r"_(aws|azure|gcp)(?:_1000)?$", source.stem)[1]
    generator = ROOT / "generators" / f"generate_{provider}_focus_1_2.py"
    errors = []
    for key, path in (("data_sha256", source), ("generator_sha256", generator)):
        if digest(path) != expected[key]:
            errors.append(f"{path.name} differs from the reviewed {key}")
    runtime = json.loads((EVIDENCE / "runtime.json").read_text(encoding="utf-8"))
    for key in ("model_sha256", "currency_codes_sha256"):
        if expected[key] != runtime[key]:
            errors.append(f"unreviewed {key}")
    return errors


def failure_examples(rows, failures):
    """Check the affected populations behind every reviewed failing leaf rule."""
    examples = {}
    for rule_id, count in failures.items():
        key = rule_id.removeprefix("CAU-")
        candidates = None
        if key in ("BillingAccountId-C-002-M", "SubAccountId-C-001-M", "CapacityReservationStatus-C-004-C", "InvoiceId-C-004-C"):
            candidates = list(enumerate(rows, 1))
        elif key in ("CommitmentDiscountStatus-C-003-C", "CommitmentDiscountStatus-C-004-C"):
            candidates = [(i, r) for i, r in enumerate(rows, 1) if not r["CommitmentDiscountId"]]
        elif key == "EffectiveCost-C-005-C":
            candidates = [(i, r) for i, r in enumerate(rows, 1) if r["ChargeCategory"] == "Purchase" and not r["CommitmentDiscountId"]]
        elif key in ("PricingCurrencyContractedUnitPrice-C-012-C", "ResourceType-C-005-C"):
            candidates = [(i, r) for i, r in enumerate(rows, 1) if r["ChargeCategory"] == "Tax"]
        elif key.startswith("ContractAppliedObject-O-"):
            predicate = None
            if key.endswith("039-C"):
                predicate = lambda e, r: e["ContractCommitmentId"] != r["ResourceId"]
            elif key[-5:] in ("051-C", "052-M", "060-C", "061-M"):
                predicate = lambda e, r: "ContractCommitmentAppliedQuantity" not in e
            elif key.endswith("065-C"):
                predicate = lambda e, r: "ContractCommitmentAppliedUnit" in e
            if predicate:
                candidates = [(i, r) for i, r in enumerate(rows, 1) if r["ContractApplied"]
                              for e in json.loads(r["ContractApplied"])["Elements"] if predicate(e, r)]
        if candidates is None:
            if count != 1:
                raise ValueError(f"Unreviewed failing population: {rule_id}")
            examples[rule_id] = {"composite_failure": True, "see": "failure-explanations.json"}
        else:
            if len(candidates) != count:
                raise ValueError(f"Wrong explanation for {rule_id}: {len(candidates)} records versus {count}")
            fields = ("ChargeCategory", "ChargeDescription", "BillingAccountId", "SubAccountId", "ResourceId",
                      "ResourceType", "CommitmentDiscountId", "CommitmentDiscountStatus", "CapacityReservationId",
                      "CapacityReservationStatus", "BilledCost", "EffectiveCost", "SkuPriceId", "ContractApplied")
            examples[rule_id] = {"measured_affected_records": count, "examples": [
                {"data_record": i, "values": {k: r[k] for k in fields if k in r}} for i, r in candidates[:2]]}
    return examples


def sample_paths():
    """Validate this provider suite even when other sample families coexist."""
    names = [f"focus_sample_costandusage_{p}_1000.csv" for p in audit.PROVIDERS]
    return [DATA / name for name in sorted(names)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-existing", action="store_true")
    mode.add_argument("--record", type=Path, metavar="DIR")
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE / "local")
    args = parser.parse_args(argv)
    expected = json.loads((EVIDENCE / "expected.json").read_text(encoding="utf-8"))
    if set(expected) != {p.name for p in sample_paths()}:
        raise ValueError("reviewed evidence must cover every provider file exactly")
    runtime = json.loads((EVIDENCE / "runtime.json").read_text(encoding="utf-8"))
    metrics, samples, examples = {}, {}, {}
    for provider in audit.PROVIDERS:
        with (DATA / f"focus_sample_costandusage_{provider}_1000.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        contracts = None
        path = DATA / f"focus_sample_contractcommitment_{provider}.csv"
        if path.exists():
            with path.open(newline="", encoding="utf-8") as f:
                contracts = list(csv.DictReader(f))
        errors = audit.audit_rows(rows, provider, contracts) if contracts is not None else audit.audit_rows(rows, provider)
        if errors:
            print("Independent audit failed:", "\n".join(errors[:10]))
            return 1
        metrics[provider] = audit.fixture_metrics(rows, provider)
        samples[provider] = rows
    if not args.check_existing:
        import focus_validator
        if importlib.metadata.version("focus-validator") != runtime["validator"]:
            raise RuntimeError("Use recorded focus-validator version")
        package = Path(focus_validator.__file__).resolve().parent
        for name, key in (("model-1.2.0.1.json", "model_sha256"), ("currency_codes.csv", "currency_codes_sha256")):
            if digest(package / "rules" / name) != runtime[key]:
                raise RuntimeError(f"Unreviewed validator resource: {name}")
        output = (args.record or args.output_dir).resolve()
        if args.record and (output == EVIDENCE.resolve() or EVIDENCE.resolve() / "after" == output or output == EVIDENCE.resolve() / "before"):
            raise ValueError("Record candidates separately; inspect before promoting")
        output.mkdir(parents=True, exist_ok=True)
    recorded, manifests, failed_files = {}, {}, 0
    for source in sample_paths():
        provider = re.search(r"_(aws|azure|gcp)(?:_1000)?$", source.stem)[1]
        snapshot = expected.get(source.name)
        if not args.record:
            errors = snapshot_errors(source, snapshot) if snapshot else ["unreviewed CSV"]
            if errors:
                print(source.name, errors); failed_files += 1; continue
        if args.check_existing:
            text = (EVIDENCE / "after" / (source.stem + ".log")).read_text(encoding="utf-8")
        else:
            dataset = "ContractCommitment" if "contractcommitment" in source.name else "CostAndUsage"
            command = [sys.executable, "-m", "focus_validator.main", "--data-file", str(source),
                       "--validate-version", "1.2.0.1", "--focus-dataset", dataset,
                       "--applicability-criteria", "ALL", "--show-violations", "--block-download"]
            result = subprocess.run(command, cwd=package.parent, capture_output=True,
                                    env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))
            raw = result.stdout + result.stderr
            (output / (source.stem + ".log")).write_bytes(raw)
            if result.returncode:
                print(f"FAIL {source.name}: validator exited {result.returncode}"); failed_files += 1; continue
            text = raw.decode("utf-8")
        report = parse_report(text)
        if args.record:
            candidate = {key: report[key] for key in ("rules", "failures", "skipped_rules")}
            candidate.update(data_sha256=digest(source), generator_sha256=digest(ROOT / "generators" / f"generate_{provider}_focus_1_2.py"),
                             model_sha256=runtime["model_sha256"], currency_codes_sha256=runtime["currency_codes_sha256"])
            recorded[source.name] = candidate
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            manifest = dict(candidate, dataset=dataset, model="1.2.0.1", validator=runtime["validator"],
                            base_revision=revision, result=report, exit_code=0,
                            command="focus-validator --data-file FOCUS-1.2/" + source.name + " --validate-version 1.2.0.1 --focus-dataset " + dataset + " --applicability-criteria ALL --show-violations --block-download")
            (output / (source.stem + ".json")).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            manifests[source.name] = report
            if dataset == "CostAndUsage":
                examples[provider] = failure_examples(samples[provider], report["failures"])
            unknown = set(report["failures"]) - set(snapshot["failures"] if snapshot else [])
            if unknown:
                print("NEW FAILURES REQUIRE INVESTIGATION:", sorted(unknown)); failed_files += 1
        else:
            errors = check_report(text, snapshot)
            if errors:
                print(source.name, errors); failed_files += 1
        print(f"{source.name}: {report['failed']} failing, {report['passed']} passing, {report['skipped']} skipped rules", flush=True)
    if args.record:
        for name, value in (("expected.json", recorded), ("metrics.json", metrics), ("failure-examples.json", examples)):
            (output / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        table = "| File | Pass | Fail | Skipped |\n|---|---:|---:|---:|\n"
        for name, r in manifests.items():
            table += f"| {name} | {r['passed']} | {r['failed']} | {r['skipped']} |\n"
        (output / "summary.md").write_text(table, encoding="utf-8")
        print("Candidate evidence recorded; expectations were NOT accepted or replaced.")
    else:
        print("Reviewed artifacts and skipped rules are NOT conformance passes.")
    return int(bool(failed_files))


if __name__ == "__main__":
    raise SystemExit(main())
