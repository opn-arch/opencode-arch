"""Learning loop: pattern classification, adaptation, assessment, and maintenance."""
from opencode_arch.learning.classifier import classify_failures
from opencode_arch.learning.adapter import get_adaptations, apply_adaptations
from opencode_arch.learning.assessor import generate_report_card, ReportCard
from opencode_arch.learning.lessons import extract_lessons, Lesson
from opencode_arch.learning.maintainer import detect_drift, auto_fix_drift, DriftFlag

__all__ = [
    "classify_failures",
    "get_adaptations",
    "apply_adaptations",
    "generate_report_card",
    "ReportCard",
    "extract_lessons",
    "Lesson",
    "detect_drift",
    "auto_fix_drift",
    "DriftFlag",
]
