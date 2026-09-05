"""Fingerprint the shared generation sources, including newly added/removed modules."""

import hashlib
import json


def source_manifest(root, version, provider):
    core = root / "generators" / "focus_sample_core"
    paths = []
    for path in core.rglob("*.py"):
        # These explicit extensions do not enter the 1.2 dependency graph.
        if version == "1_2" and (
            path.name == "v1_3.py" or path.name.endswith("_contracts.py")
        ):
            continue
        paths.append(path)
    paths.extend(
        (
            root / "generators" / f"generate_{provider}_focus_{version}.py",
            root / "generators" / "source_provenance.py",
        )
    )
    sources = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths, key=lambda p: p.relative_to(root).as_posix())
    }
    encoded = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "source_manifest": sources,
        "sources_sha256": hashlib.sha256(encoded).hexdigest(),
    }
