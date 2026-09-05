"""Non-regression against the frozen pre-extraction commits, not regenerated expectations."""

import ast
import hashlib
import importlib
import json
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from focus_sample_core.engine import Engine
from focus_sample_core.profiles.aws import PROFILE as AWS
from focus_sample_core.versions.v1_2 import ADAPTER as V12
from source_provenance import source_manifest

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = [
    v
    for v in ("1_2", "1_3")
    if (ROOT / "generators" / f"generate_aws_focus_{v}.py").exists()
]
REFERENCES = {
    "1_2": "977f8184411ae332ee5d384ae34556281e0e3b10",
    "1_3": "743dd9b01ac74594b5370340460209adfb1a1ee6",
}


def module(provider, version):
    return importlib.import_module(f"generate_{provider}_focus_{version}")


class SharedEngineTests(unittest.TestCase):
    def test_all_frozen_cases_and_published_files(self):
        for version in VERSIONS:
            directory = ROOT / f"FOCUS-{version.replace('_', '.')}"
            reference = json.loads(
                (directory / "validation/refactor-baseline.json").read_text()
            )
            self.assertEqual(reference["revision"], REFERENCES[version])
            self.assertEqual(len(reference["cases"]), 216 if version == "1_2" else 324)
            for case in reference["cases"]:
                with self.subTest(version=version, **case):
                    gen = module(case["provider"], version)
                    if case["dataset"] == "contract_commitment":
                        payload = gen.generate_contract_commitment_csv_bytes(
                            case["rows"], case["seed"]
                        )
                    else:
                        payload = gen.generate_csv_bytes(
                            case["rows"], case["seed"], include_credits=case["credits"]
                        )
                    self.assertEqual(
                        hashlib.sha256(payload).hexdigest(), case["sha256"]
                    )
            for name, expected in reference["published"].items():
                self.assertEqual(
                    hashlib.sha256((directory / name).read_bytes()).hexdigest(),
                    expected,
                )
            # These semantic statistics and explanations are independent of source-code layout.
            for name in ("dataset-statistics.json", "failure-explanations.json"):
                # Git may check out documentation JSON as CRLF on Windows. CSV bytes
                # above are compared without normalization; metadata uses Git's LF form.
                content = (
                    (directory / "validation" / name)
                    .read_bytes()
                    .replace(b"\r\n", b"\n")
                )
                self.assertEqual(
                    hashlib.sha256(content).hexdigest(), reference["artifacts"][name]
                )

    def test_entrypoints_only_delegate_and_share_builders(self):
        for version in VERSIONS:
            for provider in ("aws", "azure", "gcp"):
                gen = module(provider, version)
                self.assertIs(gen.ENGINE.__class__, Engine)
                self.assertIs(gen.ENGINE._tax_row.__func__, Engine._tax_row)
                self.assertIs(
                    gen.ENGINE._commitment_group.__func__, Engine._commitment_group
                )
                source = ast.parse(Path(gen.__file__).read_text())
                for node in source.body:
                    if isinstance(node, ast.FunctionDef):
                        self.assertEqual(len(node.body), 1, node.name)
                        self.assertIsInstance(node.body[0], ast.Return, node.name)
                        self.assertIsInstance(node.body[0].value, ast.Call, node.name)
                self.assertFalse(
                    any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(source))
                )

    def test_fake_provider_requires_only_a_profile(self):
        fake = replace(
            AWS,
            key="fake",
            provider_name="FakeCloud",
            publisher_name="FakeCloud",
            invoice_issuer="FakeCloud",
            resource_id=lambda rng, spec, region, ctx, name: (
                f"fake://{ctx['sub_id']}/{region}/{name}"
            ),
            commitment_id=lambda rng, region, ctx, kind, spend: (
                f"fake://commit/{region}/{kind}"
            ),
        )
        engine = Engine(fake, V12)
        rows = engine.generate_rows(1000, 1202)
        self.assertTrue(all(r["ProviderName"] == "FakeCloud" for r in rows))
        self.assertTrue(
            any(r["ResourceId"].startswith("urn:focus-sample:fake:") for r in rows)
        )
        self.assertEqual(
            engine.generate_csv_bytes(100, 42), engine.generate_csv_bytes(100, 42)
        )
        if "1_3" in VERSIONS:
            source = module("aws", "1_3").PROFILE
            adapter = module("aws", "1_3").ADAPTER
            fake = replace(
                fake,
                negotiated_terms=source.negotiated_terms,
                negotiated_contract_id="FAKE-CONTRACT",
            )
            engine = Engine(fake, adapter)
            from focus_sample_core.versions.v1_3 import (
                generate_contract_commitment_rows,
            )

            contracts = generate_contract_commitment_rows(engine, 100, 42)
            self.assertTrue(any(r["ContractId"] == "FAKE-CONTRACT" for r in contracts))

    def test_generation_state_does_not_leak(self):
        for version in VERSIONS:
            aws = module("aws", version)
            before = aws.generate_csv_bytes(1000, 42, include_credits=True)
            for other_version in VERSIONS:
                for provider in ("azure", "gcp", "aws"):
                    other = module(provider, other_version)
                    other.generate_rows(1000, 0)
                    if other_version == "1_3":
                        first = other.generate_contract_commitment_csv_bytes(1000, 42)
                        other.generate_rows(1000, 7)
                        self.assertEqual(
                            first,
                            other.generate_contract_commitment_csv_bytes(1000, 42),
                        )
            self.assertEqual(
                before, aws.generate_csv_bytes(1000, 42, include_credits=True)
            )

    def test_cli_and_importlib_auditor_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "sample.csv"
            for version in VERSIONS:
                audit = importlib.import_module(f"check_focus_{version}_samples")
                for provider in ("aws", "azure", "gcp"):
                    gen = audit._load(provider)
                    command = [
                        sys.executable,
                        str(
                            ROOT
                            / "generators"
                            / f"generate_{provider}_focus_{version}.py"
                        ),
                        "--rows",
                        "25",
                        "--seed",
                        "7",
                        "--out",
                        str(target),
                        "--include-credits",
                    ]
                    subprocess.run(command, check=True, capture_output=True, cwd=ROOT)
                    self.assertEqual(
                        target.read_bytes(),
                        gen.generate_csv_bytes(25, 7, include_credits=True),
                    )
                    if version == "1_3":
                        subprocess.run(
                            command + ["--dataset", "contract_commitment"],
                            check=True,
                            capture_output=True,
                            cwd=ROOT,
                        )
                        self.assertEqual(
                            target.read_bytes(),
                            gen.generate_contract_commitment_csv_bytes(25, 7),
                        )

    def test_provenance_covers_shared_changes_additions_and_removals(self):
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp)
            shutil.copytree(
                ROOT / "generators/focus_sample_core",
                copied / "generators/focus_sample_core",
            )
            for name in ("source_provenance.py", "generate_aws_focus_1_2.py"):
                shutil.copyfile(
                    ROOT / "generators" / name, copied / "generators" / name
                )
            baseline = source_manifest(copied, "1_2", "aws")
            self.assertEqual(baseline, source_manifest(ROOT, "1_2", "aws"))
            path = copied / "generators/focus_sample_core/engine.py"
            original = path.read_bytes()
            path.write_bytes(original + b"\n# modified common implementation\n")
            self.assertNotEqual(source_manifest(copied, "1_2", "aws"), baseline)
            path.write_bytes(original)
            added = path.with_name("new_helper.py")
            added.write_text("# added implementation\n")
            self.assertNotEqual(source_manifest(copied, "1_2", "aws"), baseline)
            added.unlink()
            path.unlink()
            self.assertNotEqual(source_manifest(copied, "1_2", "aws"), baseline)


if __name__ == "__main__":
    unittest.main()
