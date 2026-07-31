"""Export training corpus from .architecture/ artifacts.

Collects (model, manifest, metrics) triples from one or more repos
and writes them as JSONL for LLM training.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def run_export_data(
    repos: list[str],
    output: str = "corpus.jsonl",
    include_telemetry: bool = False,
) -> None:
    """Export .architecture/ artifacts from repos to JSONL.

    Each line is a JSON object with:
      - repo: repository name
      - model_yaml: raw YAML content of .architecture-model.yaml
      - manifest: parsed manifest.json dict
      - metrics: parsed metrics.json dict
      - telemetry_records: (optional) list of telemetry DB records
    """
    records = []

    for repo_str in repos:
        repo = Path(repo_str).resolve()
        if not repo.is_dir():
            print(f"Warning: {repo} is not a directory, skipping", file=sys.stderr)
            continue

        model_path = repo / ".architecture-model.yaml"
        arch_dir = repo / ".architecture"

        if not model_path.exists() and not arch_dir.exists():
            print(f"Warning: No .architecture-model.yaml or .architecture/ in {repo}, skipping",
                  file=sys.stderr)
            continue

        record: dict = {"repo": repo.name}

        # Model YAML (raw text for training)
        if model_path.exists():
            record["model_yaml"] = model_path.read_text()

        # Manifest
        manifest_path = arch_dir / "manifest.json" if arch_dir.exists() else None
        if manifest_path and manifest_path.exists():
            record["manifest"] = json.loads(manifest_path.read_text())

        # Metrics
        metrics_path = arch_dir / "metrics.json" if arch_dir.exists() else None
        if metrics_path and metrics_path.exists():
            record["metrics"] = json.loads(metrics_path.read_text())

        # Sub-block artifacts
        if arch_dir and arch_dir.exists():
            blocks = {}
            for block_dir in sorted(arch_dir.iterdir()):
                if block_dir.is_dir():
                    block = {}
                    block_model = block_dir / ".architecture-model.yaml"
                    if block_model.exists():
                        block["model_yaml"] = block_model.read_text()
                    block_manifest = block_dir / "manifest.json"
                    if block_manifest.exists():
                        block["manifest"] = json.loads(block_manifest.read_text())
                    block_metrics = block_dir / "metrics.json"
                    if block_metrics.exists():
                        block["metrics"] = json.loads(block_metrics.read_text())
                    if block:
                        blocks[block_dir.name] = block
            if blocks:
                record["blocks"] = blocks

        # Telemetry records (from SQLite DB)
        if include_telemetry:
            try:
                from opencode_arch.telemetry.store import TelemetryStore
                store = TelemetryStore()
                all_records = store.query(repo=repo.name)
                if all_records:
                    record["telemetry_records"] = [
                        r._asdict() if hasattr(r, '_asdict') else r
                        for r in all_records
                    ]
            except Exception:
                pass

        records.append(record)

    if not records:
        print("No data found to export.", file=sys.stderr)
        sys.exit(1)

    # Write JSONL
    output_path = Path(output)
    with output_path.open("w") as f:
        for record in records:
            f.write(json.dumps(record, default=str) + "\n")

    print(f"Exported {len(records)} repo(s) to {output_path}")
    total_size = output_path.stat().st_size
    if total_size > 1024 * 1024:
        print(f"  Size: {total_size / 1024 / 1024:.1f} MB")
    else:
        print(f"  Size: {total_size / 1024:.1f} KB")
