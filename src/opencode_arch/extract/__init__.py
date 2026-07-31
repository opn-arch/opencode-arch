"""
Extract architecture models from source code or Tier 1 artifacts.
"""

from .from_code import extract_from_code
from .from_artifacts import extract_from_artifacts

__all__ = ["extract_from_code", "extract_from_artifacts"]
