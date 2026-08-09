"""
Extract architecture models from source code or Tier 1 artifacts.

Note: route_detector, constraint_detector, from_artifacts, and table_parser
have been moved to architecture-model-standard (architecture_model.extract.*).
This package re-exports from there for backward compatibility.
"""

from architecture_model.extract.from_code import extract_from_code
from architecture_model.extract.from_artifacts import extract_from_artifacts

__all__ = ["extract_from_code", "extract_from_artifacts"]
