"""Tests for lifecycle_exec.apply — proposal apply runner (T18)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from architecture_model.ai.proposals import (
    ArtifactCandidate,
    DecompositionProposal,
    ImpactAssessment,
    ModelPatch,
    Provenance,
    SliceProposal,
    ViewCurationProposal,
)
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.publication import PackageBundle, publish
from architecture_model.lifecycle.versions import SchemaVersions

from opencode_arch.lifecycle_exec.apply import (
    ApplyReport,
    DriftError,
    InvalidProposalError,
    PackageNotFoundError,
    apply_proposal,
)


ROOT_ID = "root-pkg"

MODEL_YAML = (
    "meta:\n"
    "  project: t\n"
    "  schema_version: '1.3'\n"
    "entities:\n"
    "  components:\n"
    "    - id: COMP-1\n"
    "      name: Alpha\n"
    "      status: ACTIVE\n"
    "    - id: COMP-2\n"
    "      name: Beta\n"
    "      status: ACTIVE\n"
)


def _write_root_package(repo: Path) -> Path:
    lifecycle = repo / ".architecture" / "lifecycle"
    lifecycle.mkdir(parents=True, exist_ok=True)
    (lifecycle / "package.yaml").write_text(
        yaml.safe_dump(
            {
                "architecture_id": ROOT_ID,
                "name": "Root",
                "slug": ROOT_ID,
                "contract_version": SchemaVersions.PACKAGE,
                "model_ref": "model/.architecture-model.yaml",
                "manifest_ref": "manifest/manifest.json",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return lifecycle


def _publish_initial(repo: Path):
    lifecycle = _write_root_package(repo)
    pkg = load_package(lifecycle)
    result = publish(
        pkg,
        PackageBundle(
            model_bytes=MODEL_YAML.encode("utf-8"),
            manifest_bytes=b"{}",
        ),
    )
    return pkg, result


def _prov(model_version: str) -> Provenance:
    return Provenance(
        work_order_id="wo-1",
        model_version=model_version,
        prompt_digest="sha256:aaa",
    )


# ---------------------------------------------------------------- ImpactAssessment


def test_impact_assessment_dry_run_is_noop(tmp_path):
    proposal = ImpactAssessment(
        provenance=_prov("does-not-matter"),
        affected_ids=["COMP-1"],
        summary="hi",
    )
    report = apply_proposal(tmp_path, proposal, dry_run=True)
    assert isinstance(report, ApplyReport)
    assert report.changes == []
    assert report.new_revision is None
    assert report.digest is None
    assert len(report.journal_events) == 1
    ev = report.journal_events[0]
    assert ev["event"] == "ai.proposal.apply.impact_assessment_noop"
    assert ev["payload"]["proposal_id"] == "wo-1"
    # No journal file should have been written.
    assert not (tmp_path / ".architecture" / "lifecycle" / "journal.jsonl").exists()


def test_impact_assessment_non_dry_run_still_noop_but_records_journal(tmp_path):
    proposal = ImpactAssessment(
        provenance=_prov("x"), affected_ids=[], summary=""
    )
    report = apply_proposal(tmp_path, proposal, dry_run=False)
    assert report.changes == []
    assert report.new_revision is None
    jpath = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    assert jpath.exists()
    lines = [
        json.loads(l) for l in jpath.read_text(encoding="utf-8").splitlines() if l
    ]
    assert lines[-1]["event"] == "ai.proposal.apply.impact_assessment_noop"


# ---------------------------------------------------------------- ModelPatch


def test_model_patch_dry_run_no_side_effects(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal = ModelPatch(
        provenance=_prov(res.root_digest),
        operations=[{"op": "remove", "target_id": "COMP-2"}],
    )
    report = apply_proposal(tmp_path, proposal, dry_run=True)
    assert report.new_revision is None
    assert report.digest is None
    assert report.changes and report.changes[0]["op"] == "remove"
    # Still only generation 1 on disk.
    gens = list((tmp_path / ".architecture" / "lifecycle" / "generations").iterdir())
    assert len(gens) == 1
    assert report.journal_events[0]["event"] == "ai.proposal.apply.model_patch"


def test_model_patch_non_dry_run_publishes_new_generation(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal = ModelPatch(
        provenance=_prov(res.root_digest),
        operations=[{"op": "remove", "target_id": "COMP-2"}],
    )
    report = apply_proposal(tmp_path, proposal, dry_run=False)
    assert report.new_revision == "0000002"
    assert report.digest is not None and report.digest != res.root_digest
    # Model actually mutated.
    current_model = (
        tmp_path
        / ".architecture"
        / "lifecycle"
        / "CURRENT"
        / "model"
        / ".architecture-model.yaml"
    )
    data = yaml.safe_load(current_model.read_text(encoding="utf-8"))
    ids = {c["id"] for c in data["entities"]["components"]}
    assert ids == {"COMP-1"}
    # Journal has the apply event AND publish begin/commit events from Phase 1.
    jpath = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    events = [
        json.loads(l)["event"]
        for l in jpath.read_text(encoding="utf-8").splitlines()
        if l
    ]
    assert "ai.proposal.apply.model_patch" in events


def test_model_patch_drift_error(tmp_path):
    _publish_initial(tmp_path)
    proposal = ModelPatch(
        provenance=_prov("sha256:notthepublishedone"),
        operations=[{"op": "remove", "target_id": "COMP-1"}],
    )
    with pytest.raises(DriftError) as excinfo:
        apply_proposal(tmp_path, proposal, dry_run=True)
    assert excinfo.value.expected == "sha256:notthepublishedone"
    assert excinfo.value.actual is not None


def test_model_patch_drift_accepts_revision_string(tmp_path):
    """proposal.provenance.model_version may be the padded generation string."""
    _publish_initial(tmp_path)
    proposal = ModelPatch(
        provenance=_prov("0000001"),
        operations=[{"op": "remove", "target_id": "COMP-2"}],
    )
    # Should not raise.
    report = apply_proposal(tmp_path, proposal, dry_run=True)
    assert report.journal_events[0]["event"] == "ai.proposal.apply.model_patch"


def test_model_patch_missing_package(tmp_path):
    proposal = ModelPatch(
        provenance=_prov("x"),
        operations=[{"op": "remove", "target_id": "COMP-1"}],
    )
    with pytest.raises(PackageNotFoundError):
        apply_proposal(tmp_path, proposal, dry_run=True)


# ---------------------------------------------------------------- Decomposition


def test_decomposition_dry_run_no_files(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal = DecompositionProposal(
        provenance=_prov(res.root_digest),
        proposed_systems=[
            {"id": "child-a", "name": "Child A"},
            {"id": "child-b", "name": "Child B"},
        ],
    )
    report = apply_proposal(tmp_path, proposal, dry_run=True)
    assert report.new_revision is None
    assert len(report.changes) == 2
    ev = report.journal_events[0]
    assert ev["event"] == "ai.proposal.apply.decomposition"
    assert ev["payload"]["children"] == ["child-a", "child-b"]
    assert not (tmp_path / ".architecture" / "lifecycle" / "child-a").exists()


def test_decomposition_non_dry_run_creates_children(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal = DecompositionProposal(
        provenance=_prov(res.root_digest),
        proposed_systems=[{"id": "child-a", "name": "Child A"}],
    )
    report = apply_proposal(tmp_path, proposal, dry_run=False)
    assert report.new_revision == "0000002"
    assert report.digest is not None
    lifecycle = tmp_path / ".architecture" / "lifecycle"
    assert (lifecycle / "child-a" / "package.yaml").exists()
    child = yaml.safe_load(
        (lifecycle / "child-a" / "package.yaml").read_text(encoding="utf-8")
    )
    assert child["architecture_id"] == "child-a"
    # Parent package.yaml records the child.
    parent = yaml.safe_load(
        (lifecycle / "package.yaml").read_text(encoding="utf-8")
    )
    assert "child-a" in parent["children"]


def test_decomposition_drift_error(tmp_path):
    _publish_initial(tmp_path)
    proposal = DecompositionProposal(
        provenance=_prov("sha256:wrong"),
        proposed_systems=[{"id": "c1", "name": "C1"}],
    )
    with pytest.raises(DriftError):
        apply_proposal(tmp_path, proposal, dry_run=True)


# ---------------------------------------------------------------- Slice/View/Artifact


SLICE_SPEC = {
    "id": "slice-1",
    "name": "Slice 1",
    "some_field": "value",
    "z_field": "z",
    "a_field": "a",
}


def test_slice_proposal_dry_run_no_file(tmp_path):
    proposal = SliceProposal(provenance=_prov("x"), slice=SLICE_SPEC)
    report = apply_proposal(tmp_path, proposal, dry_run=True)
    assert report.new_revision is None
    assert report.digest is None
    assert report.changes[0]["slice_id"] == "slice-1"
    assert report.journal_events[0]["event"] == "ai.proposal.apply.slice_persisted"
    assert not (
        tmp_path / ".architecture" / "lifecycle" / "slices" / "slice-1.yaml"
    ).exists()


def test_slice_proposal_non_dry_run_writes_canonical_yaml(tmp_path):
    proposal = SliceProposal(provenance=_prov("x"), slice=SLICE_SPEC)
    report = apply_proposal(tmp_path, proposal, dry_run=False)
    path = tmp_path / ".architecture" / "lifecycle" / "slices" / "slice-1.yaml"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    # sort_keys=True: 'a_field' first, 'z_field' last.
    lines = [l for l in text.splitlines() if l and ":" in l]
    keys = [l.split(":", 1)[0].strip() for l in lines]
    assert keys.index("a_field") < keys.index("z_field")
    assert report.journal_events[0]["event"] == "ai.proposal.apply.slice_persisted"


def test_view_proposal_non_dry_run_writes(tmp_path):
    spec = {"id": "view-1", "name": "V"}
    proposal = ViewCurationProposal(provenance=_prov("x"), view_spec=spec)
    report = apply_proposal(tmp_path, proposal, dry_run=False)
    assert (
        tmp_path / ".architecture" / "lifecycle" / "views" / "view-1.yaml"
    ).exists()
    assert report.journal_events[0]["event"] == "ai.proposal.apply.view_persisted"


def test_view_proposal_dry_run_no_file(tmp_path):
    spec = {"id": "view-1", "name": "V"}
    proposal = ViewCurationProposal(provenance=_prov("x"), view_spec=spec)
    apply_proposal(tmp_path, proposal, dry_run=True)
    assert not (
        tmp_path / ".architecture" / "lifecycle" / "views" / "view-1.yaml"
    ).exists()


def test_artifact_candidate_non_dry_run_writes(tmp_path):
    spec = {"id": "art-1", "renderer": "svg"}
    proposal = ArtifactCandidate(provenance=_prov("x"), artifact_spec=spec)
    report = apply_proposal(tmp_path, proposal, dry_run=False)
    path = (
        tmp_path
        / ".architecture"
        / "lifecycle"
        / "artifacts_specs"
        / "art-1.yaml"
    )
    assert path.exists()
    assert (
        report.journal_events[0]["event"]
        == "ai.proposal.apply.artifact_spec_persisted"
    )


def test_artifact_candidate_dry_run_no_file(tmp_path):
    spec = {"id": "art-1", "renderer": "svg"}
    proposal = ArtifactCandidate(provenance=_prov("x"), artifact_spec=spec)
    apply_proposal(tmp_path, proposal, dry_run=True)
    assert not (
        tmp_path
        / ".architecture"
        / "lifecycle"
        / "artifacts_specs"
        / "art-1.yaml"
    ).exists()


# ---------------------------------------------------------------- input handling


def test_accepts_dict_and_dispatches(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal_dict = {
        "kind": "model-patch",
        "provenance": {
            "work_order_id": "wo-1",
            "model_version": res.root_digest,
            "prompt_digest": "sha256:aaa",
        },
        "operations": [{"op": "remove", "target_id": "COMP-2"}],
    }
    report = apply_proposal(tmp_path, proposal_dict, dry_run=True)
    assert report.journal_events[0]["event"] == "ai.proposal.apply.model_patch"


def test_malformed_dict_raises_invalid_proposal(tmp_path):
    with pytest.raises(InvalidProposalError):
        apply_proposal(tmp_path, {"kind": "not-a-kind"}, dry_run=True)


def test_malformed_dict_missing_provenance_raises(tmp_path):
    with pytest.raises(InvalidProposalError):
        apply_proposal(
            tmp_path,
            {"kind": "impact-assessment", "affected_ids": [], "summary": ""},
            dry_run=True,
        )


# ---------------------------------------------------------------- C1: path traversal


@pytest.mark.parametrize(
    "bad_id",
    ["../evil", "../../etc/x", "/etc/passwd", "a/b", "a\\b", "..", "", "a/../b"],
)
def test_slice_id_traversal_rejected(tmp_path, bad_id):
    spec = {"id": bad_id, "name": "x"}
    proposal = SliceProposal(provenance=_prov("x"), slice=spec)
    with pytest.raises(InvalidProposalError) as ei:
        apply_proposal(tmp_path, proposal, dry_run=False)
    assert "id" in str(ei.value).lower() or "slice" in str(ei.value).lower()
    # No file escape happened.
    assert not (tmp_path.parent / "evil.yaml").exists()


@pytest.mark.parametrize("bad_id", ["../evil", "/abs/path", "a/b", ".."])
def test_view_id_traversal_rejected(tmp_path, bad_id):
    spec = {"id": bad_id, "name": "V"}
    proposal = ViewCurationProposal(provenance=_prov("x"), view_spec=spec)
    with pytest.raises(InvalidProposalError):
        apply_proposal(tmp_path, proposal, dry_run=False)


@pytest.mark.parametrize("bad_id", ["../evil", "/abs", "a/b", ".."])
def test_artifact_id_traversal_rejected(tmp_path, bad_id):
    spec = {"id": bad_id, "renderer": "svg"}
    proposal = ArtifactCandidate(provenance=_prov("x"), artifact_spec=spec)
    with pytest.raises(InvalidProposalError):
        apply_proposal(tmp_path, proposal, dry_run=False)


@pytest.mark.parametrize("bad_slug", ["../evil", "/abs", "a/b", "..", ""])
def test_decomposition_slug_traversal_rejected(tmp_path, bad_slug):
    _, res = _publish_initial(tmp_path)
    proposal = DecompositionProposal(
        provenance=_prov(res.root_digest),
        proposed_systems=[{"id": bad_slug, "name": "X"}],
    )
    with pytest.raises(InvalidProposalError):
        apply_proposal(tmp_path, proposal, dry_run=False)
    # Parent unchanged.
    parent = yaml.safe_load(
        (tmp_path / ".architecture" / "lifecycle" / "package.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert not parent.get("children")


# ---------------------------------------------------------------- C2: atomic decomposition


def test_decomposition_rollback_on_child_write_failure(tmp_path, monkeypatch):
    """If publish or child write fails, no partial on-disk state remains."""
    _, res = _publish_initial(tmp_path)
    proposal = DecompositionProposal(
        provenance=_prov(res.root_digest),
        proposed_systems=[
            {"id": "child-a", "name": "A"},
            {"id": "child-b", "name": "B"},
        ],
    )
    # Force publish to fail after staging.
    from opencode_arch.lifecycle_exec import apply as apply_mod

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(apply_mod, "publish", boom)

    parent_before = (
        tmp_path / ".architecture" / "lifecycle" / "package.yaml"
    ).read_text(encoding="utf-8")
    gens_before = sorted(
        (tmp_path / ".architecture" / "lifecycle" / "generations").iterdir()
    )

    with pytest.raises(RuntimeError):
        apply_proposal(tmp_path, proposal, dry_run=False)

    lifecycle = tmp_path / ".architecture" / "lifecycle"
    # No child dirs stranded in place.
    assert not (lifecycle / "child-a").exists()
    assert not (lifecycle / "child-b").exists()
    # No leftover staging dirs.
    staging = [p for p in lifecycle.iterdir() if p.name.startswith(".staging-")]
    assert staging == []
    # Parent package.yaml unchanged.
    assert (lifecycle / "package.yaml").read_text(encoding="utf-8") == parent_before
    # No new generation.
    gens_after = sorted((lifecycle / "generations").iterdir())
    assert gens_after == gens_before


def test_decomposition_atomic_ordering_parent_rewritten_only_after_publish(
    tmp_path, monkeypatch
):
    """Parent package.yaml must not be rewritten until publish succeeds."""
    _, res = _publish_initial(tmp_path)
    proposal = DecompositionProposal(
        provenance=_prov(res.root_digest),
        proposed_systems=[{"id": "child-a", "name": "A"}],
    )

    from opencode_arch.lifecycle_exec import apply as apply_mod

    parent_path = tmp_path / ".architecture" / "lifecycle" / "package.yaml"
    parent_before = parent_path.read_text(encoding="utf-8")

    def failing_publish(*a, **k):
        # By the time publish is called, parent on disk must be UNCHANGED.
        assert parent_path.read_text(encoding="utf-8") == parent_before
        raise RuntimeError("publish failed")

    monkeypatch.setattr(apply_mod, "publish", failing_publish)

    with pytest.raises(RuntimeError):
        apply_proposal(tmp_path, proposal, dry_run=False)

    # And still unchanged after.
    assert parent_path.read_text(encoding="utf-8") == parent_before


def test_decomposition_duplicate_slug_raises(tmp_path):
    _, res = _publish_initial(tmp_path)
    # First apply succeeds.
    p1 = DecompositionProposal(
        provenance=_prov(res.root_digest),
        proposed_systems=[{"id": "child-a", "name": "A"}],
    )
    apply_proposal(tmp_path, p1, dry_run=False)
    # Second apply with same slug should raise.
    _, res2_digest = None, None
    pkg = load_package(tmp_path / ".architecture" / "lifecycle")
    # need new drift version — read current digest
    digest_path = pkg.root / "CURRENT" / "digest.json"
    cur_digest = json.loads(digest_path.read_text(encoding="utf-8"))["root_digest"]
    p2 = DecompositionProposal(
        provenance=_prov(cur_digest),
        proposed_systems=[{"id": "child-a", "name": "A dup"}],
    )
    with pytest.raises(InvalidProposalError):
        apply_proposal(tmp_path, p2, dry_run=False)


# ---------------------------------------------------------------- C3: model-patch validation


def test_model_patch_remove_missing_target_raises(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal = ModelPatch(
        provenance=_prov(res.root_digest),
        operations=[{"op": "remove", "target_id": "COMP-DOES-NOT-EXIST"}],
    )
    with pytest.raises(InvalidProposalError) as ei:
        apply_proposal(tmp_path, proposal, dry_run=True)
    assert "COMP-DOES-NOT-EXIST" in str(ei.value)


def test_model_patch_replace_missing_target_raises(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal = ModelPatch(
        provenance=_prov(res.root_digest),
        operations=[
            {"op": "replace", "target_id": "NOPE", "value": {"name": "X"}}
        ],
    )
    with pytest.raises(InvalidProposalError) as ei:
        apply_proposal(tmp_path, proposal, dry_run=True)
    assert "NOPE" in str(ei.value)


def test_model_patch_add_duplicate_id_raises(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal = ModelPatch(
        provenance=_prov(res.root_digest),
        operations=[
            {
                "op": "add",
                "collection": "components",
                "value": {"id": "COMP-1", "name": "dup"},
            }
        ],
    )
    with pytest.raises(InvalidProposalError) as ei:
        apply_proposal(tmp_path, proposal, dry_run=True)
    assert "COMP-1" in str(ei.value)


# ---------------------------------------------------------------- C4: move op


def test_model_patch_move_op_raises_not_supported(tmp_path):
    _, res = _publish_initial(tmp_path)
    proposal = ModelPatch(
        provenance=_prov(res.root_digest),
        operations=[
            {"op": "move", "target_id": "COMP-1", "value": {"to": "COMP-2"}}
        ],
    )
    with pytest.raises(InvalidProposalError) as ei:
        apply_proposal(tmp_path, proposal, dry_run=True)
    assert "move" in str(ei.value).lower()
