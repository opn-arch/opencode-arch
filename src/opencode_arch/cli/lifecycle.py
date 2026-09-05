"""CLI subcommands for lifecycle + AI operations (T22).

Handlers accept an argparse.Namespace and optional injection kwargs
(``_publish``, ``_apply``, ``_rebuild``, ``_merge``, ``_registry``,
``_materialize``) so tests can substitute fakes without monkey-patching
module globals. Each handler returns an int exit code:

* 0 — success
* 1 — domain error (drift, not-found, precondition failure)
* 2 — usage / validation error (argparse handles most; a few early
    checks return 2 for consistency)
* 3 — internal error / MergeIntegrityError / unknown exception

The module intentionally avoids importing from ``opencode_arch.mcp.*``
(Phase 2 exit criterion 3: lifecycle_exec must be standalone).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

_REV_RE = re.compile(r"^\d{7}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "repo", None) or ".").resolve()


def _emit(payload: dict, args: argparse.Namespace, *, human: str | None = None) -> None:
    if getattr(args, "json", False):
        print(json.dumps(payload, default=str))
        return
    if human is not None:
        print(human)
        return
    for k, v in payload.items():
        print(f"{k}: {v}")


def _parse_slice_ids(value: str) -> list[str]:
    parts = [x.strip() for x in value.split(",")]
    if any(not p for p in parts):
        raise argparse.ArgumentTypeError(
            "slice-ids entries must be non-empty (comma-separated)"
        )
    return parts


def _load_yaml_file(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _exit_and_msg(exc: BaseException) -> tuple[int, str]:
    """Map lifecycle_exec / federation exceptions to (exit_code, message).

    Uses class name to avoid importing the exception classes eagerly.
    """
    from opencode_arch.lifecycle_exec.apply import (
        DriftError,
        InvalidProposalError,
        PackageNotFoundError,
    )
    from opencode_arch.lifecycle_exec.federation import (
        PackageNotFoundInFederationError,
    )
    from opencode_arch.lifecycle_exec.merge import MergeIntegrityError

    if isinstance(exc, PackageNotFoundError):
        return 1, "Package not found"
    if isinstance(exc, PackageNotFoundInFederationError):
        return 1, "Package not found in federation"
    if isinstance(exc, DriftError):
        return 1, f"Drift detected: expected={exc.expected} actual={exc.actual}"
    if isinstance(exc, InvalidProposalError):
        return 1, f"Invalid proposal: {exc}"
    if isinstance(exc, MergeIntegrityError):
        return 3, "Merge integrity error"
    first_line = (str(exc) or type(exc).__name__).splitlines()[0]
    return 3, f"Internal error: {first_line}"


def _ensure_root_package(*_args, **_kwargs):  # pragma: no cover - removed helper
    raise RuntimeError(
        "_ensure_root_package has been removed. Use `publish --init-package "
        "--architecture-id <id>` to initialize a package explicitly."
    )


# ---------------------------------------------------------------------------
# lifecycle handlers
# ---------------------------------------------------------------------------


def cmd_lifecycle_publish(args, *, _publish=None) -> int:
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.publication import PackageBundle
    from architecture_model.lifecycle.publication import publish as _real_publish
    from architecture_model.lifecycle.versions import SchemaVersions
    from opencode_arch.lifecycle_exec import paths as _paths

    repo = _repo(args)
    model_path = Path(args.model)
    if not model_path.is_file():
        print(f"Model file not found: {model_path}", file=sys.stderr)
        return 1

    manifest_bytes = b""
    if getattr(args, "manifest", None):
        mpath = Path(args.manifest)
        if not mpath.is_file():
            print(f"Manifest file not found: {mpath}", file=sys.stderr)
            return 1
        manifest_bytes = mpath.read_bytes()

    lifecycle_root = repo / ".architecture" / "lifecycle"
    pkg_yaml = lifecycle_root / "package.yaml"

    init_package = bool(getattr(args, "init_package", False))
    arch_id = getattr(args, "architecture_id", None)
    pkg_name = getattr(args, "package_name", None)
    parent = getattr(args, "parent", None)

    # ---- Pre-write validation (no filesystem mutation before this passes).
    if init_package:
        if not arch_id:
            print(
                "--init-package requires --architecture-id",
                file=sys.stderr,
            )
            return 2
        if pkg_yaml.exists():
            print("Package already initialized", file=sys.stderr)
            return 1
        # Parent must match the package we're about to create (or be None).
        if parent is not None and parent != arch_id:
            print(f"Parent package {parent!r} not found", file=sys.stderr)
            return 1
    else:
        if not pkg_yaml.exists():
            print("Package not found", file=sys.stderr)
            return 1
        pkg_probe = load_package(lifecycle_root)
        if parent is not None and parent != pkg_probe.architecture_id:
            print(f"Parent package {parent!r} not found", file=sys.stderr)
            return 1

    # ---- All checks passed; now perform any writes.
    tree = _paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]
    pkg_yaml = lifecycle_root / "package.yaml"

    if init_package:
        pkg_yaml.write_text(
            yaml.safe_dump(
                {
                    "architecture_id": arch_id,
                    "name": pkg_name or arch_id,
                    "slug": arch_id,
                    "contract_version": SchemaVersions.PACKAGE,
                    "model_ref": "model/.architecture-model.yaml",
                    "manifest_ref": "manifest/manifest.json",
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    pkg = load_package(lifecycle_root)

    model_bytes = model_path.read_bytes()
    fn = _publish or _real_publish
    try:
        result = fn(
            pkg,
            PackageBundle(model_bytes=model_bytes, manifest_bytes=manifest_bytes),
            journal_path=_paths.journal_path(repo),
        )
    except Exception as exc:  # noqa: BLE001
        code, msg = _exit_and_msg(exc)
        print(msg, file=sys.stderr)
        return code

    revision = f"{result.generation:07d}"
    payload = {
        "package_id": pkg.architecture_id,
        "revision": revision,
        "digest": result.root_digest,
        "generation_dir": str(result.generation_dir),
    }
    _emit(
        payload,
        args,
        human=(
            f"Published {pkg.architecture_id}@{revision} "
            f"digest={result.root_digest[:12] if result.root_digest else '-'}"
        ),
    )
    return 0


def cmd_lifecycle_load(args, *, _registry=None) -> int:
    if getattr(args, "federated", False):
        from opencode_arch.lifecycle_exec.federation import FederatedRegistry

        reg = _registry if _registry is not None else FederatedRegistry()
        try:
            root, desc = reg.resolve(args.package_id, getattr(args, "revision", None))
        except Exception as exc:  # noqa: BLE001
            code, msg = _exit_and_msg(exc)
            print(msg, file=sys.stderr)
            return code
        payload = {
            "package_id": desc.id,
            "revision": desc.revision,
            "digest": desc.digest,
            "path": str(desc.path),
            "root": str(root),
        }
        _emit(payload, args, human=f"{desc.id}@{desc.revision} ({root})")
        return 0

    # In-repo resolution.
    from architecture_model.lifecycle import generation_dir
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.publication import (
        list_generations,
        read_current_generation,
    )
    from opencode_arch.lifecycle_exec import paths as _paths

    repo = _repo(args)
    tree = _paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]
    if not (lifecycle_root / "package.yaml").exists():
        print("Package not found", file=sys.stderr)
        return 1
    pkg = load_package(lifecycle_root)
    if pkg.architecture_id != args.package_id:
        print(f"Package {args.package_id!r} not found", file=sys.stderr)
        return 1

    rev = getattr(args, "revision", None)
    if rev is None:
        current = read_current_generation(pkg)
        if current is None:
            print("No published generation", file=sys.stderr)
            return 1
        n = current
    else:
        if not _REV_RE.match(rev):
            print(
                "Invalid revision format (expected 7-digit zero-padded integer)",
                file=sys.stderr,
            )
            return 2
        n = int(rev)
        if n not in list_generations(pkg):
            print(f"Generation {rev} not found", file=sys.stderr)
            return 1

    gen_dir = generation_dir(pkg, n)
    payload = {
        "package_id": pkg.architecture_id,
        "revision": f"{n:07d}",
        "generation_dir": str(gen_dir),
    }
    _emit(payload, args, human=f"{pkg.architecture_id}@{payload['revision']}")
    return 0


def cmd_lifecycle_stale(args) -> int:
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.stale import build_graph
    from opencode_arch.lifecycle_exec import paths as _paths

    repo = _repo(args)
    tree = _paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]
    if not (lifecycle_root / "package.yaml").exists():
        print("Package not found", file=sys.stderr)
        return 1
    root_pkg = load_package(lifecycle_root)
    try:
        graph = build_graph(root_pkg)
    except Exception as exc:  # noqa: BLE001
        code, msg = _exit_and_msg(exc)
        print(msg, file=sys.stderr)
        return code

    nodes = [
        {"node_id": n.node_id, "kind": n.kind, "digest": n.digest}
        for n in graph.nodes()
    ]
    nodes.sort(key=lambda n: (n["kind"], n["node_id"]))
    _emit(
        {"nodes": nodes},
        args,
        human="\n".join(f"[{n['kind']}] {n['node_id']}" for n in nodes) or "(no nodes)",
    )
    return 0


def cmd_lifecycle_slice(args, *, _materialize=None) -> int:
    from architecture_model.lifecycle.model_slice import ModelSlice
    from architecture_model.lifecycle.model_slice_materializer import (
        materialize as _real_materialize,
    )
    from architecture_model.lifecycle.package import load_package
    from opencode_arch.lifecycle_bridge import resolve_current_pkg
    from opencode_arch.lifecycle_exec import paths as _paths

    repo = _repo(args)
    curation_path = Path(args.curation)
    if not curation_path.is_file():
        print(f"Curation file not found: {curation_path}", file=sys.stderr)
        return 1
    try:
        if curation_path.suffix.lower() == ".json":
            curation = json.loads(curation_path.read_text(encoding="utf-8"))
        else:
            curation = _load_yaml_file(curation_path)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"Invalid curation file: {exc}", file=sys.stderr)
        return 1
    if not isinstance(curation, dict):
        print("Curation must be a mapping", file=sys.stderr)
        return 1
    curation.setdefault("id", args.id)

    tree = _paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]
    if not (lifecycle_root / "package.yaml").exists():
        print("Package not found", file=sys.stderr)
        return 1
    pkg = load_package(lifecycle_root)
    pkg = resolve_current_pkg(pkg)

    try:
        slice_obj = ModelSlice(**curation)
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid slice: {exc}".splitlines()[0], file=sys.stderr)
        return 1

    fn = _materialize or _real_materialize
    try:
        ms = fn(slice_obj, pkg)
    except FileNotFoundError:
        print("Package model not found", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        code, msg = _exit_and_msg(exc)
        print(msg, file=sys.stderr)
        return code

    out_dir = lifecycle_root / "slices"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{slice_obj.id}.yaml"
    target.write_text(
        yaml.safe_dump(curation, sort_keys=True, default_flow_style=False),
        encoding="utf-8",
    )
    _emit(
        {"slice_id": ms.slice_id, "path": str(target)},
        args,
        human=f"Wrote {target}",
    )
    return 0


def _load_specs_dir(specs_dir: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Scan ``specs_dir`` for artifact/view/slice specs.

    Layout: subdirectories ``artifacts/``, ``views/``, ``slices/`` each
    containing ``*.yaml`` files. Missing subdirs are treated as empty.
    """
    def _load_all(sub: str) -> list[dict]:
        d = specs_dir / sub
        if not d.is_dir():
            return []
        specs = []
        for p in sorted(d.glob("*.yaml")):
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                specs.append(data)
        return specs

    return _load_all("artifacts"), _load_all("views"), _load_all("slices")


def cmd_lifecycle_rebuild(args, *, _rebuild=None) -> int:
    from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts as _real

    specs_dir = Path(args.specs)
    if not specs_dir.is_dir():
        print(f"Specs directory not found: {specs_dir}", file=sys.stderr)
        return 1
    artifact_specs, view_specs, slice_specs = _load_specs_dir(specs_dir)

    fn = _rebuild or _real
    try:
        report = fn(
            _repo(args),
            artifact_specs,
            view_specs,
            slice_specs,
            force=bool(getattr(args, "force", False)),
        )
    except Exception as exc:  # noqa: BLE001
        code, msg = _exit_and_msg(exc)
        print(msg, file=sys.stderr)
        return code

    payload = report.to_dict()
    _emit(
        payload,
        args,
        human=(
            f"built={len(report.built)} "
            f"skipped={len(report.skipped)} "
            f"failed={len(report.failed)}"
        ),
    )
    return 0


def cmd_lifecycle_merge(args, *, _merge=None, _publish=None) -> int:
    for label, rev in (
        ("base", args.base),
        ("local", args.local),
        ("remote", args.remote),
    ):
        if not _REV_RE.match(rev):
            print(
                f"Invalid {label} revision {rev!r} "
                "(expected 7-digit zero-padded integer)",
                file=sys.stderr,
            )
            return 2

    from architecture_model.core.parser import load_model
    from architecture_model.lifecycle import generation_dir
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.publication import (
        PackageBundle,
        list_generations,
    )
    from architecture_model.lifecycle.publication import publish as _real_publish
    from opencode_arch.lifecycle_exec import paths as _paths
    from opencode_arch.lifecycle_exec.merge import (
        MergeIntegrityError,
        three_way_merge as _real_merge,
    )

    repo = _repo(args)
    tree = _paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]
    if not (lifecycle_root / "package.yaml").exists():
        print("Package not found", file=sys.stderr)
        return 1
    pkg = load_package(lifecycle_root)
    gens = list_generations(pkg)
    for label, rev in (
        ("base", args.base),
        ("local", args.local),
        ("remote", args.remote),
    ):
        if int(rev) not in gens:
            print(
                f"Package not found: {label} revision {rev}", file=sys.stderr
            )
            return 1

    loaded: dict = {}
    for label, rev in (
        ("base", args.base),
        ("local", args.local),
        ("remote", args.remote),
    ):
        try:
            loaded[label] = load_model(
                generation_dir(pkg, int(rev)) / "model" / ".architecture-model.yaml"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Malformed model in {label} revision {rev}: {exc}", file=sys.stderr)
            return 1

    merge_fn = _merge or _real_merge
    try:
        result = merge_fn(loaded["base"], loaded["local"], loaded["remote"])
    except MergeIntegrityError:
        print("Merge integrity error", file=sys.stderr)
        return 3
    except Exception as exc:  # noqa: BLE001
        code, msg = _exit_and_msg(exc)
        print(msg, file=sys.stderr)
        return code

    if result.conflicts:
        conflicts = [
            {
                "entity_id": c.entity_id,
                "field": c.field,
                "base": c.base,
                "local": c.local,
                "remote": c.remote,
            }
            for c in result.conflicts
        ]
        payload = {
            "merged": False,
            "conflicts": conflicts,
            "stats": dict(result.stats),
        }
        _emit(
            payload,
            args,
            human=f"Conflicts: {len(conflicts)}",
        )
        return 1

    # Publish merged model.
    merged_bytes = result.merged_model.to_yaml().encode("utf-8")
    manifest_path = (
        generation_dir(pkg, int(args.local)) / "manifest" / "manifest.json"
    )
    manifest_bytes = manifest_path.read_bytes() if manifest_path.is_file() else b""
    fn = _publish or _real_publish
    try:
        pub = fn(
            pkg,
            PackageBundle(model_bytes=merged_bytes, manifest_bytes=manifest_bytes),
            journal_path=_paths.journal_path(repo),
        )
    except Exception as exc:  # noqa: BLE001
        code, msg = _exit_and_msg(exc)
        print(msg, file=sys.stderr)
        return code

    payload = {
        "merged": True,
        "merged_revision": f"{pub.generation:07d}",
        "merged_digest": pub.root_digest,
        "stats": dict(result.stats),
    }
    _emit(
        payload,
        args,
        human=f"Merged into revision {payload['merged_revision']}",
    )
    return 0


# ---------------------------------------------------------------------------
# ai handlers
# ---------------------------------------------------------------------------


def cmd_ai_submit(args) -> int:
    from architecture_model.ai.jobs import JobStore
    from architecture_model.ai.work_order import WorkOrder
    from architecture_model.lifecycle.atomic_store import write_atomic

    repo = _repo(args)
    wo_path_in = Path(args.work_order)
    if not wo_path_in.is_file():
        print(f"WorkOrder file not found: {wo_path_in}", file=sys.stderr)
        return 1
    try:
        data = _load_yaml_file(wo_path_in)
    except yaml.YAMLError as exc:
        print(f"Invalid work_order YAML: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("work_order must be a mapping", file=sys.stderr)
        return 1
    try:
        wo = WorkOrder.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Invalid work_order: {exc}", file=sys.stderr)
        return 1

    errors = wo.validate_schema()
    if errors:
        print("Invalid work_order: " + "; ".join(errors), file=sys.stderr)
        return 1

    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    wo_path = wo_dir / f"{wo.id}.yaml"
    if wo_path.exists():
        print(f"WorkOrder {wo.id!r} already exists", file=sys.stderr)
        return 1
    write_atomic(
        wo_path,
        yaml.safe_dump(wo.to_dict(), sort_keys=True, default_flow_style=False).encode(
            "utf-8"
        ),
    )

    store = JobStore(root=repo)
    job = store.create(work_order_id=wo.id, actor=wo.requested_by)

    _emit(
        {"work_order_id": wo.id, "job_id": job.id},
        args,
        human=f"Submitted work_order={wo.id} job={job.id}",
    )
    return 0


def cmd_ai_job_get(args) -> int:
    from architecture_model.ai.jobs import JobStore

    repo = _repo(args)
    store = JobStore(root=repo)
    try:
        job = store.get(args.job_id)
    except KeyError:
        print(f"Job {args.job_id!r} not found", file=sys.stderr)
        return 1
    _emit(
        job.to_dict(),
        args,
        human=f"Job {job.id}: state={job.state.value} work_order={job.work_order_id}",
    )
    return 0


def cmd_ai_job_transition(args) -> int:
    from architecture_model.ai.jobs import (
        InvalidTransitionError,
        JobState,
        JobStore,
    )

    repo = _repo(args)
    valid = sorted(s.value for s in JobState)
    try:
        target = JobState(args.new_state)
    except ValueError:
        print(
            f"Invalid new_state {args.new_state!r}; valid: {', '.join(valid)}",
            file=sys.stderr,
        )
        return 2

    store = JobStore(root=repo)
    try:
        job = store.transition(
            args.job_id,
            target,
            reason=None,
            actor="cli",
            result_ref=getattr(args, "result_ref", None),
            error=getattr(args, "error", None),
        )
    except KeyError:
        print(f"Job {args.job_id!r} not found", file=sys.stderr)
        return 1
    except InvalidTransitionError as exc:
        print(f"Invalid transition: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Invalid transition: {exc}", file=sys.stderr)
        return 1

    _emit(
        job.to_dict(),
        args,
        human=f"Transitioned {job.id} → {target.value}",
    )
    return 0


def cmd_ai_proposal_validate(args) -> int:
    from architecture_model.ai.proposals import proposal_from_dict
    from architecture_model.ai.validators import validate as validate_proposal
    from architecture_model.ai.work_order import WorkOrder

    repo = _repo(args)
    try:
        slice_ids = _parse_slice_ids(args.slice_ids)
    except argparse.ArgumentTypeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    prop_path = Path(args.proposal)
    if not prop_path.is_file():
        print(f"Proposal file not found: {prop_path}", file=sys.stderr)
        return 1
    prop_data = _load_yaml_file(prop_path)
    if not isinstance(prop_data, dict):
        print("proposal must be a mapping", file=sys.stderr)
        return 1
    try:
        proposal = proposal_from_dict(prop_data)
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid proposal: {exc}".splitlines()[0], file=sys.stderr)
        return 1

    wo_path = (
        repo / ".architecture" / "ai" / "workorders" / f"{args.workorder_id}.yaml"
    )
    if not wo_path.exists():
        print(f"WorkOrder {args.workorder_id!r} not found", file=sys.stderr)
        return 1
    try:
        wo = WorkOrder.from_dict(_load_yaml_file(wo_path))
    except Exception as exc:  # noqa: BLE001
        print(f"WorkOrder malformed: {exc}", file=sys.stderr)
        return 1

    slices_dir = repo / ".architecture" / "lifecycle" / "slices"
    input_slices: dict[str, dict] = {}
    for sid in slice_ids:
        sp = slices_dir / f"{sid}.yaml"
        if not sp.exists():
            print(f"Slice {sid!r} not found", file=sys.stderr)
            return 1
        d = _load_yaml_file(sp) or {}
        input_slices[sid] = d if isinstance(d, dict) else {}

    report = validate_proposal(
        proposal, work_order=wo, input_slices=input_slices
    )
    payload = {
        "passed": report.passed,
        "findings": [f.to_dict() for f in report.findings],
    }
    _emit(
        payload,
        args,
        human=(
            f"Validation: {'PASS' if report.passed else 'FAIL'} "
            f"findings={len(report.findings)}"
        ),
    )
    return 0 if report.passed else 1


def cmd_ai_proposal_apply(args, *, _apply=None) -> int:
    from architecture_model.ai.proposals import proposal_from_dict
    from opencode_arch.lifecycle_exec.apply import (
        DriftError,
        InvalidProposalError,
        PackageNotFoundError,
        apply_proposal as _real_apply,
    )
    from opencode_arch.lifecycle_exec.federation import (
        PackageNotFoundInFederationError,
    )

    repo = _repo(args)
    prop_path = Path(args.proposal)
    if not prop_path.is_file():
        print(f"Proposal file not found: {prop_path}", file=sys.stderr)
        return 1
    data = _load_yaml_file(prop_path)
    if not isinstance(data, dict):
        print("proposal must be a mapping", file=sys.stderr)
        return 1
    try:
        proposal = proposal_from_dict(data)
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid proposal: {exc}".splitlines()[0], file=sys.stderr)
        return 1

    fn = _apply or _real_apply
    try:
        report = fn(repo, proposal, dry_run=bool(getattr(args, "dry_run", False)))
    except DriftError as exc:
        print(
            f"Drift detected: expected={exc.expected} actual={exc.actual}",
            file=sys.stderr,
        )
        return 1
    except InvalidProposalError as exc:
        print(f"Invalid proposal: {exc}", file=sys.stderr)
        return 1
    except PackageNotFoundError:
        print("Package not found", file=sys.stderr)
        return 1
    except PackageNotFoundInFederationError:
        print("Package not found in federation", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:  # noqa: BLE001
        first_line = (str(exc) or type(exc).__name__).splitlines()[0]
        print(f"Internal error: {first_line}", file=sys.stderr)
        return 3

    payload = _json_safe(dataclasses.asdict(report))
    _emit(
        payload,
        args,
        human=(
            f"Applied (dry_run={bool(getattr(args, 'dry_run', False))}) "
            f"new_revision={report.new_revision}"
        ),
    )
    return 0


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Argparse registration
# ---------------------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--repo", default=None, help="Repo root (default: CWD)")
    p.add_argument(
        "--json", action="store_true", help="Emit structured JSON on stdout"
    )


def register_lifecycle_subparsers(subparsers) -> None:
    lc = subparsers.add_parser(
        "lifecycle", help="Lifecycle package operations (publish/load/stale/…)"
    )
    lc_sub = lc.add_subparsers(dest="lifecycle_command", required=True)

    pub = lc_sub.add_parser(
        "publish",
        help=(
            "Publish an architecture package. Requires an existing "
            "package.yaml; pass --init-package --architecture-id <id> to "
            "create one."
        ),
    )
    pub.add_argument("--model", required=True, help="Path to model YAML")
    pub.add_argument("--manifest", default=None, help="Path to manifest JSON")
    pub.add_argument("--parent", default=None, help="Parent package id")
    pub.add_argument(
        "--init-package",
        action="store_true",
        dest="init_package",
        help=(
            "Create the package descriptor if missing. Requires "
            "--architecture-id. Fails if a package already exists."
        ),
    )
    pub.add_argument(
        "--architecture-id",
        dest="architecture_id",
        default=None,
        help="Architecture id to use when initializing a new package.",
    )
    pub.add_argument(
        "--package-name",
        dest="package_name",
        default=None,
        help="Human-readable package name (defaults to --architecture-id).",
    )
    _add_common(pub)

    ld = lc_sub.add_parser("load", help="Load a published package generation")
    ld.add_argument("package_id")
    ld.add_argument("--revision", default=None, help="7-digit generation id")
    ld.add_argument(
        "--federated",
        action="store_true",
        help="Resolve via FederatedRegistry",
    )
    _add_common(ld)

    st = lc_sub.add_parser("stale", help="Report stale nodes in the package graph")
    _add_common(st)

    sl = lc_sub.add_parser("slice", help="Materialize a model slice")
    sl.add_argument("--id", required=True, help="Slice id")
    sl.add_argument(
        "--curation", required=True, help="Path to curation YAML/JSON"
    )
    _add_common(sl)

    rb = lc_sub.add_parser("rebuild", help="Rebuild artifacts from spec dir")
    rb.add_argument("--specs", required=True, help="Spec directory")
    rb.add_argument("--force", action="store_true", help="Force rebuild")
    _add_common(rb)

    mg = lc_sub.add_parser("merge", help="Three-way merge of three revisions")
    mg.add_argument("--base", required=True)
    mg.add_argument("--local", required=True)
    mg.add_argument("--remote", required=True)
    _add_common(mg)


def register_ai_subparsers(subparsers) -> None:
    ai = subparsers.add_parser(
        "ai", help="AI WorkOrder / Job / Proposal operations"
    )
    ai_sub = ai.add_subparsers(dest="ai_command", required=True)

    sm = ai_sub.add_parser("submit", help="Submit a WorkOrder")
    sm.add_argument(
        "--work-order", required=True, dest="work_order", help="Path to WorkOrder YAML"
    )
    _add_common(sm)

    job = ai_sub.add_parser("job", help="Job operations")
    job_sub = job.add_subparsers(dest="job_command", required=True)

    jg = job_sub.add_parser("get", help="Fetch a Job by id")
    jg.add_argument("job_id")
    _add_common(jg)

    jt = job_sub.add_parser("transition", help="Transition a Job to a new state")
    jt.add_argument("job_id")
    jt.add_argument("new_state")
    jt.add_argument("--result-ref", dest="result_ref", default=None)
    jt.add_argument("--error", default=None)
    _add_common(jt)

    pr = ai_sub.add_parser("proposal", help="Proposal operations")
    pr_sub = pr.add_subparsers(dest="proposal_command", required=True)

    pv = pr_sub.add_parser("validate", help="Validate a Proposal")
    pv.add_argument("--proposal", required=True, help="Path to proposal YAML")
    pv.add_argument(
        "--workorder-id", required=True, dest="workorder_id"
    )
    pv.add_argument(
        "--slice-ids",
        required=True,
        dest="slice_ids",
        help="Comma-separated slice ids",
    )
    _add_common(pv)

    pa = pr_sub.add_parser("apply", help="Apply a Proposal")
    pa.add_argument("--proposal", required=True, help="Path to proposal YAML")
    pa.add_argument("--workorder-id", required=True, dest="workorder_id")
    pa.add_argument(
        "--apply",
        action="store_false",
        dest="dry_run",
        default=True,
        help=(
            "Actually apply the proposal to the package. "
            "Default is a dry-run preview (no mutation)."
        ),
    )
    _add_common(pa)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def dispatch_lifecycle(args) -> int:
    return {
        "publish": cmd_lifecycle_publish,
        "load": cmd_lifecycle_load,
        "stale": cmd_lifecycle_stale,
        "slice": cmd_lifecycle_slice,
        "rebuild": cmd_lifecycle_rebuild,
        "merge": cmd_lifecycle_merge,
    }[args.lifecycle_command](args)


def dispatch_ai(args) -> int:
    if args.ai_command == "submit":
        return cmd_ai_submit(args)
    if args.ai_command == "job":
        return {
            "get": cmd_ai_job_get,
            "transition": cmd_ai_job_transition,
        }[args.job_command](args)
    if args.ai_command == "proposal":
        return {
            "validate": cmd_ai_proposal_validate,
            "apply": cmd_ai_proposal_apply,
        }[args.proposal_command](args)
    raise AssertionError(f"unknown ai command: {args.ai_command}")


__all__ = [
    "register_lifecycle_subparsers",
    "register_ai_subparsers",
    "dispatch_lifecycle",
    "dispatch_ai",
    "cmd_lifecycle_publish",
    "cmd_lifecycle_load",
    "cmd_lifecycle_stale",
    "cmd_lifecycle_slice",
    "cmd_lifecycle_rebuild",
    "cmd_lifecycle_merge",
    "cmd_ai_submit",
    "cmd_ai_job_get",
    "cmd_ai_job_transition",
    "cmd_ai_proposal_validate",
    "cmd_ai_proposal_apply",
]
