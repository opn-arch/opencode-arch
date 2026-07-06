"""Prompt templates for the decomposed regen-loop."""

REGEN_PROMPT = """\
## Regenerate {subsystem_name} (iteration {iteration}/{max_iterations})

You are regenerating a subsystem of a Python project. Your goal is to produce
source files that pass the associated test suite.

### Source files to produce:
{source_files}

### Architecture Model (structural)
{model_context}

### Constants (must be exact)
{constants}

### Function Signatures
{signatures}

### Test Contracts (assertions that MUST pass)
{test_contracts}

### Dependency Context
{dependency_apis}

{previous_feedback}\
"""

FEEDBACK_HEADER = """\
### Feedback from previous iteration ({prev_iteration})

The following tests failed. Fix these issues:

{failure_analysis}
"""
