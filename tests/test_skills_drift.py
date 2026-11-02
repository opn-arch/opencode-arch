"""Drift guard: the shipped skills must reference only real `arch_*` tools.

The `skills/` docs drifted badly once already — they described the legacy AMS
`architect_*` 10-stage pipeline long after the tools had moved to the openAG
`arch_*` surface. This test makes that class of drift a failing test instead of
silent rot:

* No legacy/AMS tokens (`architect_`, `uncertainties_to_resolve`,
  `.architecture-models/`) may appear in any ``SKILL.md`` — except inside an
  explicit ``<!-- legacy-ok:start -->`` / ``<!-- legacy-ok:end -->`` region,
  which is how a skill intentionally teaches that those legacy names are gone.
* Every ``arch_*`` name referenced in a skill must correspond to a real tool
  function defined under ``src/opencode_arch/mcp/tools/``.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILLS_DIR = _REPO_ROOT / "skills"
_TOOLS_DIR = _REPO_ROOT / "src" / "opencode_arch" / "mcp" / "tools"

_TOOL_DEF_RE = re.compile(r"^\s*(?:async\s+def|def)\s+(arch_[a-z0-9_]+)", re.MULTILINE)
_TOOL_REF_RE = re.compile(r"\barch_[a-z0-9_]+\b")
_LEGACY_OK_RE = re.compile(
    r"<!--\s*legacy-ok:start\s*-->.*?<!--\s*legacy-ok:end\s*-->",
    re.DOTALL,
)
_FORBIDDEN = ("architect_", "uncertainties_to_resolve", ".architecture-models/")


def _strip_legacy_regions(text: str) -> str:
    return _LEGACY_OK_RE.sub("", text)


def _real_tool_names() -> set[str]:
    names: set[str] = set()
    for path in _TOOLS_DIR.rglob("*.py"):
        names.update(_TOOL_DEF_RE.findall(path.read_text(encoding="utf-8")))
    return names


def _skill_files() -> list[Path]:
    return sorted(_SKILLS_DIR.rglob("SKILL.md"))


def test_skills_dir_present_and_nonempty():
    assert _SKILLS_DIR.is_dir(), f"missing skills dir: {_SKILLS_DIR}"
    assert _skill_files(), "no SKILL.md files found under skills/"


def test_real_tool_names_discovered():
    # Sanity: the discovery mechanism finds a plausible tool set, so an empty
    # set can never make the reference check below vacuously pass.
    names = _real_tool_names()
    assert "arch_pipeline" in names
    assert "arch_frontier" in names
    assert len(names) > 20


def test_no_legacy_tokens_in_skills():
    offenders: list[str] = []
    for path in _skill_files():
        text = _strip_legacy_regions(path.read_text(encoding="utf-8"))
        for lineno, line in enumerate(text.splitlines(), 1):
            for token in _FORBIDDEN:
                if token in line:
                    offenders.append(f"{path.name}:{lineno}: {token!r} in {line.strip()!r}")
    assert not offenders, (
        "legacy AMS tokens leaked into skills (wrap intentional teaching in a "
        "<!-- legacy-ok:start/end --> region):\n" + "\n".join(offenders)
    )


def test_referenced_tools_exist():
    valid = _real_tool_names()
    offenders: list[str] = []
    for path in _skill_files():
        for ref in sorted(set(_TOOL_REF_RE.findall(path.read_text(encoding="utf-8")))):
            if ref not in valid:
                offenders.append(f"{path.name}: references unknown tool {ref!r}")
    assert not offenders, "skills reference non-existent arch_* tools:\n" + "\n".join(offenders)
