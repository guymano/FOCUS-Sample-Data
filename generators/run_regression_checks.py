"""Run independent acceptance, regressions, frozen-output and evidence checks.

Run from any directory: python generators/run_regression_checks.py --output-dir DIR
An output directory is required; this command never updates expected results.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    versions = [
        v
        for v in ("1_2", "1_3")
        if (root / "generators" / f"generate_aws_focus_{v}.py").exists()
    ]
    commands = []
    for version in versions:
        commands.extend(
            [
                (
                    version + "-acceptance",
                    [f"generators/check_focus_{version}_samples.py"],
                ),
                (
                    version + "-regressions",
                    [
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "generators",
                        "-p",
                        f"test_focus_{version}_regressions.py",
                    ],
                ),
                (
                    version + "-statistics",
                    [f"generators/describe_focus_{version}_samples.py"],
                ),
                (
                    version + "-evidence",
                    [
                        f"generators/validate_focus_{version}_samples.py",
                        "--check-existing",
                    ],
                ),
            ]
        )
    commands.append(
        (
            "shared",
            [
                "-m",
                "unittest",
                "discover",
                "-s",
                "generators",
                "-p",
                "test_focus_shared.py",
            ],
        )
    )
    result = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "checks": [],
    }
    for label, command in commands:
        process = subprocess.run(
            [sys.executable, *command],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),
        )
        (out / (label + ".log")).write_bytes(process.stdout)
        result["checks"].append(
            {
                "command": "python " + " ".join(command),
                "exit_code": process.returncode,
                "log": label + ".log",
                "sha256": hashlib.sha256(process.stdout).hexdigest(),
            }
        )
        print(label, process.returncode, flush=True)
        if process.returncode:
            print(process.stdout.decode("utf-8", errors="replace")[-3000:], flush=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return int(any(c["exit_code"] for c in result["checks"]))


if __name__ == "__main__":
    raise SystemExit(main())
