"""Learning loop: pattern classification, adaptation, assessment, and maintenance."""
from opencode_arch.learning.classifier import classify_failures
from opencode_arch.learning.adapter import get_adaptations, apply_adaptations

__all__ = ["classify_failures", "get_adaptations", "apply_adaptations"]
