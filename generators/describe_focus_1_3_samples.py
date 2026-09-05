"""Recalculate dataset statistics; --write updates only marked README tables and statistics artifacts."""
import argparse
from collections import Counter
import csv
from decimal import Decimal
import json
import re

import validate_focus_1_3_samples as evidence
import check_focus_1_3_samples as audit


def statistics():
    output = {}
    for provider in audit.PROVIDERS:
        with (evidence.DATA / f"focus_sample_costandusage_{provider}_1000.csv").open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        item = {"categories": dict(Counter(r["ChargeCategory"] for r in rows)),
                "commitment_discounts": len({r["CommitmentDiscountId"] for r in rows if r["CommitmentDiscountId"]}),
                "used": sum(r["CommitmentDiscountStatus"] == "Used" for r in rows),
                "unused": sum(r["CommitmentDiscountStatus"] == "Unused" for r in rows),
                "effective_cost": str(sum((Decimal(r["EffectiveCost"]) for r in rows), Decimal(0))),
                "metrics": audit.fixture_metrics(rows, provider)}
        if "1.3" == "1.3":
            with (evidence.DATA / f"focus_sample_contractcommitment_{provider}.csv").open(encoding="utf-8", newline="") as f:
                contracts = list(csv.DictReader(f))
            discounts = {r["CommitmentDiscountId"] for r in rows}
            item.update(commitments=len(contracts), contracts=len({r["ContractId"] for r in contracts}),
                        non_discount_terms=sum(r["ContractCommitmentId"] not in discounts for r in contracts),
                        applied_rows=sum(bool(r["ContractApplied"]) for r in rows))
        output[provider] = item
    return output


def tables(stats):
    result = "| Provider | Usage | Purchase | Tax | Discounts | Used | Unused |\n|---|---:|---:|---:|---:|---:|---:|\n"
    for p, s in stats.items():
        c = s["categories"]
        result += f"| {p} | {c.get('Usage',0)} | {c.get('Purchase',0)} | {c.get('Tax',0)} | {s['commitment_discounts']} | {s['used']} | {s['unused']} |\n"
    result += "\n| Provider | Billed = Effective cost (USD) | Commitment share | Utilization | Waste | Compute coverage |\n|---|---:|---:|---:|---:|---:|\n"
    for p, s in stats.items():
        m = s["metrics"]
        percent = [f"{Decimal(m[k])*100:.2f}%" for k in ("commitment_share", "utilization", "waste", "coverage")]
        result += f"| {p} | {m['billed_cost']} | {' | '.join(percent)} |\n"
    if "1.3" == "1.3":
        result += "\n| Provider | Commitments | Non-discount terms | Contracts | Rows with ContractApplied |\n|---|---:|---:|---:|---:|\n"
        for p, s in stats.items():
            result += f"| {p} | {s['commitments']} | {s['non_discount_terms']} | {s['contracts']} | {s['applied_rows']} |\n"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    stats = statistics(); table = tables(stats)
    payloads = {evidence.EVIDENCE / "dataset-statistics.json": json.dumps(stats, indent=2) + "\n",
                evidence.EVIDENCE / "statistics.md": table,
                evidence.EVIDENCE / "metrics.json": json.dumps({p: s["metrics"] for p, s in stats.items()}, indent=2) + "\n"}
    readme = evidence.DATA / "README.md"
    text = readme.read_text(encoding="utf-8")
    pattern = r"<!-- BEGIN GENERATED STATISTICS -->.*?<!-- END GENERATED STATISTICS -->"
    replacement = "<!-- BEGIN GENERATED STATISTICS -->\n" + table + "<!-- END GENERATED STATISTICS -->"
    updated, count = re.subn(pattern, lambda m: replacement, text, flags=re.S)
    if count != 1:
        raise ValueError("Expected exactly one statistics block")
    payloads[readme] = updated
    for path, content in payloads.items():
        if args.write:
            path.write_text(content, encoding="utf-8", newline="\n")
        elif not path.exists() or path.read_text(encoding="utf-8") != content:
            print(f"Stale statistics: {path}"); return 1
    print("Statistics updated." if args.write else "All statistics match the current CSVs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
