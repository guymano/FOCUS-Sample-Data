"""Regression proofs, including deliberate corruptions and generation boundaries.

Run: python -m unittest discover -s generators -p 'test_focus_1_2_regressions.py'
"""
import copy
from decimal import Decimal
import json
import random
import unittest
from unittest.mock import patch

import check_focus_1_2_samples as audit


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = {p: audit._load(p) for p in audit.PROVIDERS}
        cls.samples = {p: m.generate_rows(1000, m.DEFAULT_SEED) for p, m in cls.modules.items()}

    def test_validator_coexists_with_generic_sample_files(self):
        import contextlib
        import io
        import shutil
        import tempfile
        from pathlib import Path
        import validate_focus_1_2_samples as validator
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            sources = validator.sample_paths()
            for source in sources:
                shutil.copyfile(source, data / source.name)
            for name in ("focus_sample.csv", "focus_sample_costandusage.csv", "focus_sample_contractcommitment.csv"):
                (data / name).write_text("generic sample handled by its own workflow\n", encoding="utf-8")
            with patch.object(validator, "DATA", data), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(3, len(validator.sample_paths()))
                self.assertEqual(0, validator.main(["--check-existing"]))
                (data / sources[0].name).unlink()
                with self.assertRaises(FileNotFoundError):
                    validator.main(["--check-existing"])

    def test_size_seed_credit_matrix(self):
        for provider, module in self.modules.items():
            for size in (1, 2, 11, 12, 23, 24, 25, 1000, 1001):
                for seed in (0, 1, 42, module.DEFAULT_SEED):
                    for credits in (False, True):
                        with self.subTest(provider=provider, size=size, seed=seed, credits=credits):
                            rows = module.generate_rows(size, seed, include_credits=credits)
                            self.assertEqual(len(rows), size)
                            self.assertEqual(list(rows[0]), list(audit.EXPECTED_COLUMNS))
                            self.assertEqual(audit.audit_rows(rows, provider), [])
                            first = module.generate_csv_bytes(size, seed, include_credits=credits)
                            self.assertEqual(first, module.generate_csv_bytes(size, seed, include_credits=credits))
                            self.assertNotIn(b"\r\n", first)
            with self.assertRaises(ValueError):
                module.generate_rows(0)
            with self.assertRaises(ValueError):
                module.generate_rows(-1)

    def test_stable_skus_across_seeds_accounts_and_categories(self):
        for provider, module in self.modules.items():
            with self.subTest(provider=provider):
                rows = self.samples[provider] + module.generate_rows(1000, 42)
                self.assertEqual(audit.sku_errors(rows), [])
                by_sku = {}
                for row in rows:
                    if row["SkuId"]:
                        by_sku.setdefault(row["SkuId"], []).append(row)
                self.assertTrue(any({r["PricingCategory"] for r in group} == {"Standard", "Committed"}
                                    and all(r["SkuMeter"] != "Commitment" for r in group)
                                    for group in by_sku.values()))
                self.assertTrue(any(len({r["BillingAccountId"] for r in group}) > 1 for group in by_sku.values()))

    def test_tax_oracle_and_duplicate_source_rejection(self):
        for provider, module in self.modules.items():
            source = next(r for r in self.samples[provider] if r["ChargeCategory"] == "Usage"
                          and r["PricingCategory"] == "Standard")
            source = copy.deepcopy(source)
            source.update(BilledCost="2.34", EffectiveCost="2.34", ListCost="3.45", ContractedCost="2.34",
                          PricingCurrency="EUR", PricingCurrencyEffectiveCost="2.1528")
            tax = module._tax_row(source, 1)
            self.assertEqual([Decimal(tax[k]) for k in audit.COSTS],
                             list(map(Decimal, (".234", ".234", ".345", ".234", ".21528"))))
            rows = copy.deepcopy(self.samples[provider])
            first_tax = next(r for r in rows if r["ChargeCategory"] == "Tax")
            rows.append(copy.deepcopy(first_tax))
            self.assertTrue(any(e.startswith("tax:") for e in audit.audit_rows(rows, provider)))

    def test_complete_groups_at_exact_budget(self):
        for provider, module in self.modules.items():
            for usage, unused in ((5, 1), (9, 3), (10, 4)):
                needed = 2 * (usage + unused)
                for budget in (needed - 1, needed, needed + 1):
                    with self.subTest(provider=provider, needed=needed, budget=budget):
                        rng = random.Random(7)
                        args = [rng, 0, budget]
                        registry = module._ContractRegistry() if hasattr(module, "_ContractRegistry") else None
                        if registry:
                            args.append(registry)
                            previous = list(registry.commitments)
                        with patch.object(rng, "randint", side_effect=[usage, unused]):
                            group = module._commitment_group(*args)
                        self.assertEqual(len(group), 0 if budget < needed else needed)
                        self.assertEqual(audit.audit_rows(group, provider), [])
                        if registry:
                            self.assertEqual(len(registry.commitments), len(previous) + bool(group))

    def test_corruptions_are_detected(self):
        for provider, original in self.samples.items():
            mutations = {
                "required:": lambda rows: rows[0].update(PricingCurrency=""),
                "cost:": lambda rows: next(r for r in rows if r["ChargeCategory"] == "Purchase"
                                          and not r["CommitmentDiscountId"]).update(EffectiveCost="0"),
                "tax:": lambda rows: next(r for r in rows if r["ChargeCategory"] == "Tax").update(ListCost="999"),
                "sku:": lambda rows: next(r for r in rows if r["SkuId"]).update(SkuId="different-row-id"),
                "commitment:": lambda rows: rows.remove(next(r for r in rows if r["CommitmentDiscountId"])),
            }
            if provider == "aws":
                mutations["resource:"] = lambda rows: next(r for r in rows if r["ResourceId"]
                    and not r["CommitmentDiscountId"]).update(ResourceId="arn:aws:bda:us-east-1:100000000001:function/test")
            for label, mutate in mutations.items():
                with self.subTest(provider=provider, corruption=label):
                    rows = copy.deepcopy(original)
                    mutate(rows)
                    self.assertTrue(any(e.startswith(label) for e in audit.audit_rows(rows, provider)))

    def test_standard_properties_and_prices_cannot_drift(self):
        for provider, original in self.samples.items():
            rows = copy.deepcopy(original)
            row = next(r for r in rows if '"StorageClass"' in r["SkuPriceDetails"])
            row["SkuPriceDetails"] = row["SkuPriceDetails"].replace('"StorageClass"', '"x_StorageClass"')
            self.assertTrue(audit.sku_errors(rows))
            rows = copy.deepcopy(original)
            row = next(r for r in rows if r["SkuPriceId"])
            row["ListUnitPrice"] = "999"
            self.assertTrue(audit.sku_errors(rows))



    def test_validator_report_cannot_hide_new_failures(self):
        import validate_focus_1_2_samples as validator
        text = "Total: 2 | Pass: 1 | Fail: 1 | Skipped: 0\nX Good-C-001-M: PASS  (violations=0)\nX Known-C-001-M: FAIL  (violations=2)"
        expected = validator.parse_report(text)
        self.assertEqual(validator.check_report(text, expected), [])
        self.assertTrue(validator.check_report(text.replace("Known-", "Unknown-"), expected))
        self.assertTrue(validator.check_report(text.replace("violations=2", "violations=3"), expected))
        self.assertTrue(validator.check_report("Traceback (most recent call last)", expected))
        missing = text.replace("X Good-C-001-M: PASS  (violations=0)\n", "").replace("Total: 2 | Pass: 1", "Total: 1 | Pass: 0")
        self.assertTrue(validator.check_report(missing, expected))
        self.assertTrue(validator.check_report(text + "\nX Good-C-001-M: PASS  (violations=0)", expected))
        changed = text.replace("Pass: 1", "Pass: 0").replace("Skipped: 0", "Skipped: 1").replace(": PASS ", ": SKIPPED ")
        self.assertTrue(validator.check_report(changed, expected))

    def test_evidence_checks_input_and_generator_hashes(self):
        import validate_focus_1_2_samples as validator
        source = validator.DATA / "focus_sample_costandusage_aws_1000.csv"
        expected = json.loads((validator.EVIDENCE / "expected.json").read_text(encoding="utf-8"))[source.name]
        self.assertEqual(validator.snapshot_errors(source, expected), [])
        for key in ("data_sha256", "generator_sha256", "model_sha256", "currency_codes_sha256"):
            wrong = dict(expected, **{key: "0" * 64})
            self.assertTrue(validator.snapshot_errors(source, wrong), key)

    def test_fleet_scale_and_metrics(self):
        for provider, rows in self.samples.items():
            metrics = audit.fixture_metrics(rows, provider)
            self.assertGreaterEqual(Decimal(metrics["commitment_share"]), Decimal("0.05"))
            self.assertEqual(Decimal(metrics["used_effective_cost"]) + Decimal(metrics["unused_effective_cost"]), Decimal(metrics["commitment_purchases"]))
            for key in ("utilization", "waste", "coverage"):
                self.assertTrue(0 <= Decimal(metrics[key]) <= 1, key)
            used = next(r for r in rows if r["CommitmentDiscountStatus"] == "Used")
            self.assertEqual(used["ResourceType"], "Compute Fleet")
            self.assertEqual(Decimal(used["ConsumedQuantity"]), Decimal(500))
            self.assertEqual(json.loads(used["Tags"])["SyntheticFleetSize"], "500")
            broken = copy.deepcopy(rows)
            next(r for r in broken if r["CommitmentDiscountStatus"] == "Used")["ConsumedQuantity"] = "1"
            self.assertTrue(any(e.startswith("commitment:") for e in audit.audit_rows(broken, provider)))
            excluded = [r for r in rows if r["ChargeCategory"] in ("Tax", "Purchase")]
            self.assertIsNone(audit.fixture_metrics(excluded, provider)["coverage"])


if __name__ == "__main__":
    unittest.main()
