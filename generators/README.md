# FOCUS 1.2 provider generators

Self-contained standard-library generators produce synthetic AWS, Azure and GCP
datasets. This workflow uses explicit provider tables and scenario builders.

See [dataset scenarios and generation commands](../FOCUS-1.2/README.md).

```bash
python generators/check_focus_1_2_samples.py
python -m unittest discover -s generators -p 'test_focus_1_2_regressions.py'
python generators/describe_focus_1_2_samples.py
python generators/validate_focus_1_2_samples.py --check-existing
```

[Official validation and candidate-evidence recording](../FOCUS-1.2/validation/README.md)
use an optional pinned environment. The generators and independent checks do not.
The Contract Commitment dataset, when present, joins through ContractApplied.
Contributed under the repository license (CC BY 4.0).
