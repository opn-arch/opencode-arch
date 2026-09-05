"""Federated registry resolver (T21).

Discovers architecture packages across independent registry roots on the
local filesystem. A *root* is a directory that contains one or more
published ``package.yaml`` descriptors at any depth. Roots are typically
sibling repository trees on the same machine.

Configuration is persisted at ``<config_dir>/federation.yaml`` (default
``~/.opencode-arch/federation.yaml``). No cryptographic signing — that
is deferred to Phase 3.

Public API
----------
* :class:`FederatedRegistry` — the resolver.
* :class:`PackageDescriptor` — a minimal, immutable resolution result.
* Exceptions: :class:`FederationError` (base),
  :class:`PackageNotFoundInFederationError`,
  :class:`RevisionNotFoundError`,
  :class:`AmbiguousPackageError`,
  :class:`FederationConfigError`.

Package id semantics
--------------------
The resolver matches against the ``architecture_id`` field in
``package.yaml`` (Phase 1 :class:`ArchitecturePackage` schema).

Revision semantics
------------------
* ``revision=None`` → resolve to the currently published revision
  (contents of ``<pkg>/CURRENT`` symlink). If absent, descriptor
  ``revision`` and ``digest`` are ``None``.
* Explicit ``revision`` → require that ``<pkg>/generations/<rev>``
  exists; otherwise raise :class:`RevisionNotFoundError`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

__all__ = [
    "FederatedRegistry",
    "PackageDescriptor",
    "FederationError",
    "PackageNotFoundInFederationError",
    "RevisionNotFoundError",
    "AmbiguousPackageError",
    "FederationConfigError",
]

_CONFIG_FILENAME = "federation.yaml"
_CONFIG_VERSION = 1
_SKIP_DIRS = frozenset({
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    "dist",
    "build",
})


# --- exceptions --------------------------------------------------------------

class FederationError(Exception):
    """Base class for federation errors."""


class PackageNotFoundInFederationError(FederationError):
    def __init__(self, package_id: str, searched_roots: list[Path]) -> None:
        super().__init__(
            f"package {package_id!r} not found in federation "
            f"(searched {len(searched_roots)} root(s))"
        )
        self.package_id = package_id
        self.searched_roots = list(searched_roots)


class RevisionNotFoundError(FederationError):
    def __init__(self, package_id: str, revision: str, root: Path) -> None:
        super().__init__(
            f"revision {revision!r} of package {package_id!r} not found under {root}"
        )
        self.package_id = package_id
        self.revision = revision
        self.root = root


class AmbiguousPackageError(FederationError):
    def __init__(self, package_id: str, matches: list[Path]) -> None:
        super().__init__(
            f"package {package_id!r} is ambiguous: {len(matches)} matches"
        )
        self.package_id = package_id
        self.matches = list(matches)


class FederationConfigError(FederationError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# --- descriptor --------------------------------------------------------------

@dataclass(frozen=True)
class PackageDescriptor:
    """Minimal resolution result.

    ``path`` is the absolute path to the ``package.yaml`` file.
    ``revision`` is the resolved generation directory name (e.g.
    ``"0000005"``) or ``None`` if the package has never been published.
    ``digest`` is the ``root_digest`` from that generation's
    ``digest.json`` or ``None``.
    """

    id: str
    path: Path
    revision: str | None
    digest: str | None


# --- registry ----------------------------------------------------------------

class FederatedRegistry:
    """Federated registry over local directories.

    Parameters
    ----------
    config_dir:
        Directory containing ``federation.yaml``. When ``None``, defaults
        to ``~/.opencode-arch``. The directory is created lazily on first
        write.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = (
            Path(config_dir) if config_dir is not None
            else Path.home() / ".opencode-arch"
        )
        self._roots: list[Path] = []
        # {root -> {package_id -> package.yaml path}}
        self._cache: dict[Path, dict[str, Path]] | None = None
        self._load()

    # -- config file ---------------------------------------------------------

    @property
    def config_path(self) -> Path:
        return self._config_dir / _CONFIG_FILENAME

    def _load(self) -> None:
        p = self.config_path
        if not p.exists():
            self._roots = []
            return
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            raise FederationConfigError(f"cannot read {p}: {e}") from e
        if not text.strip():
            self._roots = []
            return
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise FederationConfigError(f"malformed YAML in {p}: {e}") from e
        if data is None:
            self._roots = []
            return
        if not isinstance(data, dict):
            raise FederationConfigError(
                f"{p}: top-level YAML must be a mapping"
            )
        version = data.get("version")
        if version != _CONFIG_VERSION:
            raise FederationConfigError(
                f"{p}: unsupported version {version!r} (expected {_CONFIG_VERSION})"
            )
        raw_roots = data.get("roots", [])
        if not isinstance(raw_roots, list):
            raise FederationConfigError(
                f"{p}: 'roots' must be a list, got {type(raw_roots).__name__}"
            )
        roots: list[Path] = []
        for item in raw_roots:
            if not isinstance(item, str):
                raise FederationConfigError(
                    f"{p}: root entries must be strings"
                )
            roots.append(Path(item))
        self._roots = roots

    def _persist(self) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        doc = {
            "version": _CONFIG_VERSION,
            "roots": [str(r) for r in self._roots],
        }
        text = yaml.safe_dump(doc, sort_keys=False, default_flow_style=False)
        target = self.config_path
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)

    # -- root management -----------------------------------------------------

    def _normalize(self, path: Path | str) -> Path:
        return Path(path).expanduser().resolve()

    def add_root(self, path: Path | str) -> Path:
        p = self._normalize(path)
        if not p.exists():
            raise ValueError(f"root does not exist: {p}")
        if not p.is_dir():
            raise ValueError(f"root is not a directory: {p}")
        if p in self._roots:
            return p
        self._roots.append(p)
        self._cache = None
        self._persist()
        return p

    def remove_root(self, path: Path | str) -> None:
        try:
            p = self._normalize(path)
        except OSError:
            return
        if p not in self._roots:
            return
        self._roots = [r for r in self._roots if r != p]
        self._cache = None
        self._persist()

    def list_roots(self) -> list[Path]:
        return list(self._roots)

    def refresh(self) -> None:
        """Clear the in-memory scan cache."""
        self._cache = None

    # -- scanning ------------------------------------------------------------

    def _scan_root(self, root: Path) -> dict[str, Path]:
        """Return ``{architecture_id -> package.yaml path}`` for a root.

        Raises :class:`AmbiguousPackageError` if the same id is declared
        twice within this root.
        """
        found: dict[str, list[Path]] = {}
        for dirpath, dirnames, filenames in os.walk(root):
            # prune noise dirs in-place
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            if "package.yaml" in filenames:
                yaml_path = Path(dirpath) / "package.yaml"
                pkg_id = _read_id(yaml_path)
                if pkg_id is not None:
                    found.setdefault(pkg_id, []).append(yaml_path)
        result: dict[str, Path] = {}
        for pkg_id, paths in found.items():
            if len(paths) > 1:
                raise AmbiguousPackageError(pkg_id, paths)
            result[pkg_id] = paths[0]
        return result

    def _ensure_cache(self) -> dict[Path, dict[str, Path]]:
        if self._cache is None:
            self._cache = {r: self._scan_root(r) for r in self._roots}
        return self._cache

    # -- resolution ----------------------------------------------------------

    def resolve(
        self,
        package_id: str,
        revision: str | None = None,
    ) -> tuple[Path, PackageDescriptor]:
        """Resolve ``package_id`` (optionally at ``revision``).

        Returns ``(root, descriptor)``. Roots are searched in FIFO order
        — the first root containing a match wins.
        """
        cache = self._ensure_cache()
        for root in self._roots:
            index = cache.get(root, {})
            yaml_path = index.get(package_id)
            if yaml_path is None:
                continue
            pkg_dir = yaml_path.parent
            resolved_rev, digest = _resolve_revision(
                pkg_dir, package_id, revision, root
            )
            desc = PackageDescriptor(
                id=package_id,
                path=yaml_path,
                revision=resolved_rev,
                digest=digest,
            )
            return root, desc
        raise PackageNotFoundInFederationError(package_id, self._roots)


# --- helpers -----------------------------------------------------------------

def _read_id(yaml_path: Path) -> str | None:
    """Cheaply extract ``architecture_id`` from a package.yaml file.

    Returns ``None`` if the file cannot be parsed or the id is missing —
    the scan tolerates malformed descriptors rather than crashing.
    """
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    pkg_id = data.get("architecture_id")
    if isinstance(pkg_id, str) and pkg_id:
        return pkg_id
    return None


def _resolve_revision(
    pkg_dir: Path,
    package_id: str,
    revision: str | None,
    root: Path,
) -> tuple[str | None, str | None]:
    """Resolve a requested revision to ``(revision, digest)``.

    * ``revision is None`` → follow ``CURRENT``; if missing, return ``(None, None)``.
    * explicit ``revision`` → require ``generations/<rev>`` to exist.
    """
    gens = pkg_dir / "generations"
    if revision is None:
        current = pkg_dir / "CURRENT"
        if not current.exists() and not current.is_symlink():
            return None, None
        try:
            target = os.readlink(str(current))
        except OSError:
            return None, None
        rev_name = Path(target).name
        gen_dir = gens / rev_name
        return rev_name, _read_root_digest(gen_dir)
    gen_dir = gens / revision
    if not gen_dir.is_dir():
        raise RevisionNotFoundError(package_id, revision, root)
    return revision, _read_root_digest(gen_dir)


def _read_root_digest(gen_dir: Path) -> str | None:
    digest_file = gen_dir / "digest.json"
    if not digest_file.is_file():
        return None
    try:
        import json
        doc = json.loads(digest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(doc, dict):
        d = doc.get("root_digest")
        if isinstance(d, str):
            return d
    return None
