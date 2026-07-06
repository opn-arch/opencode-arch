"""E2E extraction benchmark: extract architecture from real repos."""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

import pytest


@pytest.mark.e2e
class TestExtraction:
    """Extract architecture from benchmark repos and verify quality."""

    TIMEOUT = 600  # 10 minutes per repo

    def test_extract_produces_valid_model(self, repo_info, results_dir, project_dir):
        """Extract architecture and verify score >= 80."""
        repo_path = str(repo_info["path"])
        repo_name = repo_info["name"]

        start = time.time()

        # Call opencode run with extraction prompt
        prompt = (
            f"Use architect_scan to scan the repository at {repo_path}, then produce "
            f"a valid .architecture-model.yaml in that directory. Use architect_extract "
            f"to validate and store it. The model must score >= 80. Include meta "
            f"(project: {repo_name}, schema_version: '1.3'), entities (capabilities, "
            f"components), and relationships (realizes, depends-on, contains). "
            f"Output the final YAML between ```yaml fences."
        )

        result = subprocess.run(
            ["opencode", "run", prompt, "--dir", str(project_dir),
             "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=self.TIMEOUT,
        )

        elapsed = time.time() - start

        # Check model was stored
        model_path = Path(repo_path) / ".architecture-model.yaml"
        assert model_path.exists(), f"No .architecture-model.yaml produced for {repo_name}"

        # Validate the stored model
        from architecture_model.core.parser import load_model
        from architecture_model.core.validator import validate_model

        model = load_model(model_path)
        validation = validate_model(model)

        # Record result
        result_data = {
            "test": "e2e_extraction",
            "timestamp": datetime.now().isoformat(),
            "repo": repo_name,
            "url": repo_info["url"],
            "score": validation.score,
            "is_valid": validation.is_valid,
            "entity_count": model.entity_count,
            "relationship_count": len(model.relationships),
            "issues": [str(i) for i in validation.issues[:10]],
            "time_seconds": elapsed,
            "exit_code": result.returncode,
        }

        # Write result
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = results_dir / f"e2e_extract_{repo_name}_{ts}.json"
        out_file.write_text(json.dumps(result_data, indent=2))

        # Assertions
        assert validation.score >= 80, (
            f"{repo_name}: score {validation.score}/100, "
            f"issues: {[str(i) for i in validation.issues[:5]]}"
        )
        assert model.entity_count >= 3, f"{repo_name}: only {model.entity_count} entities"

        # Cleanup: remove generated model (don't pollute benchmark repos)
        model_path.unlink(missing_ok=True)
