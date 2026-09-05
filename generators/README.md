# Provider sample generators

The six direct-script entry points use one standard-library generation core. No
package installation or external toolkit dependency is needed. Keep the local
`focus_sample_core` directory alongside the scripts when copying this workflow.

The core separates common scenario builders and exact serialization from immutable
provider profiles and explicit FOCUS version adapters. Provider callbacks only
format identifiers and preserve their historical random draws. RNGs, tax lineage
and contract registries are local to each generation call. The 1.2 adapter does not
import 1.3 extensions; the 1.3 adapter adds contracts and allocation to the same engine.

This extracts the corrected sample generators; it does not import the toolkit's
older sample semantics. Output compatibility is locked to the reviewed commits in
each dataset's validation/refactor-baseline.json. The independent auditors retain
their own expected values, rather than trusting the production profiles.

## Non-regression workflow

```bash
python generators/run_regression_checks.py --output-dir /path/to/check-results
```

Use an output directory outside the committed evidence. The runner executes every
version available in the checkout, including the frozen-output matrix and shared
engine tests. It never updates expected results. Official validation remains a
separate command with the pinned optional environment documented below.

## FOCUS 1.2

[Scenarios and generation commands](../FOCUS-1.2/README.md) ·
[Official validator and evidence](../FOCUS-1.2/validation/README.md).

```bash
python generators/check_focus_1_2_samples.py
python -m unittest discover -s generators -p 'test_focus_1_2_regressions.py'
python generators/describe_focus_1_2_samples.py
python generators/validate_focus_1_2_samples.py --check-existing
```

## FOCUS 1.3

[Scenarios and generation commands](../FOCUS-1.3/README.md) ·
[Official validator and evidence](../FOCUS-1.3/validation/README.md).

```bash
python generators/check_focus_1_3_samples.py
python -m unittest discover -s generators -p 'test_focus_1_3_regressions.py'
python generators/describe_focus_1_3_samples.py
python generators/validate_focus_1_3_samples.py --check-existing
```

Contributed under the repository license (CC BY 4.0).
