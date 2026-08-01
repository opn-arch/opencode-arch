# Quality Report Synthesis — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Synthesize existing benchmark, performance, and quality data into a comprehensive quality report saved as both JSON (machine-readable) and Markdown (human-readable) in `.opencode/metrics/`.

**Architecture:** Read existing data files, compute derived metrics, produce two output files: `quality-report-2026-07-31.json` (full structured data) and `quality-report-2026-07-31.md` (narrative summary with tables).

**Tech Stack:** Python 3.12, JSON, Markdown

---

### Task 1: Create the quality report JSON

**Files:**
- Read: `.opencode/metrics/benchmark-2026-07-31.json`
- Read: `.opencode/metrics/performance-2026-07-31.json`
- Read: `/tmp/arch-bench/_quality_assessment.json`
- Read: `/tmp/arch-bench/_python_metrics.json`
- Read: `/tmp/arch-bench/_nonpython_metrics.json`
- Create: `.opencode/metrics/quality-report-2026-07-31.json`

**Step 1: Write a Python script to merge all 5 data sources and compute derived metrics**

Per-repo derived metrics:
- `modules_per_component` ratio
- `confidence_tier` (excellent/good/needs_work/poor)
- `field_fill_rates` per enrichment field (% of components with field populated)

Aggregate stats (Python repos):
- Mean/median/min/max for confidence, representativeness, boundary_coherence
- Global field fill rates across all repos

Findings (8 items, severity-tagged):
1. CRITICAL: test_contracts 0% everywhere (15% confidence weight unreachable)
2. CRITICAL: Flat repos collapse to single F-block (4/10 repos)
3. HIGH: Celery boundary coherence 38.2%
4. HIGH: Non-Python repos near-zero confidence
5. HIGH: SQLAlchemy 0 interface contracts
6. MEDIUM: Django 26 low-confidence boilerplate components
7. MEDIUM: Rich trivial filter too aggressive
8. LOW: Pattern detection varies widely (0-67%)

Recommendations (6 items, prioritized):
1. Populate test_contracts (medium effort, high impact)
2. Import-affinity decomposition for flat repos (medium effort, high impact)
3. Fix trivial module filter (low effort, medium impact)
4. Non-Python enrichment pipeline (high effort, high impact)
5. Boundary-coherence-aware grouping (medium effort, medium impact)
6. Filter boilerplate components (low effort, low impact)

**Step 2: Run the script**
Run: `/opt/anaconda3/bin/python /tmp/gen_quality_report.py`

**Step 3: Verify output exists and spot-check values**

---

### Task 2: Create the Markdown quality report

**Files:**
- Read: `.opencode/metrics/quality-report-2026-07-31.json`
- Create: `.opencode/metrics/quality-report-2026-07-31.md`

**Structure:**
1. Executive Summary (3-4 sentences)
2. Benchmark Overview table (13 repos, key metrics)
3. Quality Scores table (validation, repr, boundary coherence)
4. Confidence Analysis (buckets, tiers, field fill rates)
5. Decomposition Analysis (F-blocks, flat-repo problem, Django Shared)
6. Performance Profile (wall time, scaling)
7. Findings (prioritized, severity-tagged)
8. Recommendations (prioritized, effort/impact)

**Step 1: Write the markdown file using data from the JSON report**

**Step 2: Verify by reading the file**

---

### Task 3: Commit the report

```bash
git add .opencode/metrics/quality-report-2026-07-31.json .opencode/metrics/quality-report-2026-07-31.md
git commit -m "docs: add v0.5.0 quality report from 13-repo benchmark"
```
