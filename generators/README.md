# FOCUS sample-data generators (provider-realistic, deterministic)

Deterministic Python generators that produce **provider-realistic** synthetic
**FOCUS 1.2** Cost and Usage datasets for **AWS, Azure and GCP**.

They complement the model-driven generation tooling (see PR #5 / `focusgen`):
where model-driven generation targets the validator's rule set with generic
values, these generators emit data that *looks like the provider* — realistic
services, SKUs, regions, instance types, pricing units, commitment models
(Savings Plans / Reservations / CUDs) and tax rows — while conforming to the
FOCUS column set and conditionality rules.

## Properties

- **Deterministic**: seeded RNG + fixed timestamps. A given `(rows, seed)` pair
  is byte-reproducible, so committed samples can be regenerated and diffed.
- **Synthetic / PII-free**: no real account data; account ids, resource ids and
  names are generated.
- **Self-contained**: Python 3.11+ standard library only. No dependencies.
- **Normalized across providers**: identical column sets, as the spec requires;
  only the values differ per provider.

## Scope of the emitted rows

The committed fixtures contain `Usage`, `Purchase` and `Tax` rows, including full
commitment groups — a recurring purchase per charge period, plus the `Used` and
`Unused` usage rows that amortise it. They contain **no** `Credit` rows and **no**
marketplace rows: `--include-credits` adds negative-cost `Credit` rows but is not used
for the committed samples, and `PublisherName` / `InvoiceIssuerName` hold a single value
per provider.

## Usage

```bash
python generators/generate_aws_focus_1_2.py   --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_aws_1000.csv
python generators/generate_azure_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_azure_1000.csv
python generators/generate_gcp_focus_1_2.py   --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_gcp_1000.csv
```

A follow-up PR adds the FOCUS 1.3 generators and their two datasets, and documents them
here alongside these. It depends on this one and must land after it.

## Checks

```bash
python generators/check_focus_1_2_samples.py
```

Re-runs the generators, compares them byte-for-byte with the committed CSVs, and asserts
the normative requirements the samples depend on — exact `ListCost` / `ContractedCost`
arithmetic, commitment reconciliation, the shape of purchase / `Used` / `Unused` rows,
conditional nullability, and billing-identity consistency. See `FOCUS-1.2/README.md` for
the full list.

## Validation

See `FOCUS-1.2/README.md` for the
[focus_validator](https://github.com/finopsfoundation/focus_validator) status, including
the release that was withdrawn and the run that needs re-establishing.

## License

Contributed under the repository license (CC BY 4.0).
