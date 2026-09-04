# FOCUS 1.2 sample-data generators

Deterministic, provider-shaped synthetic examples for AWS, Azure and Google Cloud.
They take a different approach from model-driven generation: they illustrate
selected provider scenarios and explicit cost relationships. Each provider's
generator remains self-contained; there is no common provider module.

Python 3.11+ and the standard library are sufficient to generate and check samples.
The official validator uses a separate optional environment.

## Generate

```bash
python generators/generate_aws_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_aws_1000.csv
python generators/generate_azure_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_azure_1000.csv
python generators/generate_gcp_focus_1_2.py --rows 1000 --seed 1202 --out FOCUS-1.2/focus_sample_costandusage_gcp_1000.csv
```

Default Cost and Usage files contain Usage, Purchase and Tax, including complete
Used/Unused commitment groups. Credits are available with `--include-credits` but
are not present in the committed samples. No marketplace data is represented.


## Check

```bash
python generators/check_focus_1_2_samples.py
python -m unittest discover -s generators -p 'test_focus_1_2_regressions.py'
python generators/validate_focus_1_2_samples.py --check-existing
```

See [the dataset README](../FOCUS-1.2/README.md) for scenarios, exact current
counts and modelling limits; [validation evidence](../FOCUS-1.2/validation/README.md)
contains before/after results and instructions for the optional official validator.
Contributed under the repository license (CC BY 4.0).
