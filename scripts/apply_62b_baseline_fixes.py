"""Apply dynamic baseline fixes for 62B."""

from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


root = Path(__file__).resolve().parents[1]

aggregation = root / "src/gridiron/research/aggregation.py"
replace_once(
    aggregation,
    "from gridiron.research.models import ResearchRun\n",
    "from gridiron.research.baseline import resolve_baseline_name\n"
    "from gridiron.research.models import ResearchRun\n",
)
replace_once(
    aggregation,
    '    baseline_name: str = "rest_000_baseline",\n',
    "    baseline_name: str | None = None,\n",
)
replace_once(
    aggregation,
    '    baseline_rows = grouped.get(baseline_name)\n'
    '    if baseline_rows is None:\n'
    '        raise ValueError(\n'
    '            f"Baseline experiment {baseline_name!r} was not found."\n'
    '        )\n',
    '    resolved_baseline = resolve_baseline_name(run, baseline_name)\n'
    '    baseline_rows = grouped[resolved_baseline]\n',
)

statistics = root / "src/gridiron/research/statistics.py"
replace_once(
    statistics,
    "from gridiron.research.models import ResearchRun\n",
    "from gridiron.research.baseline import resolve_baseline_name\n"
    "from gridiron.research.models import ResearchRun\n",
)
replace_once(
    statistics,
    '    baseline_name: str = "rest_000_baseline",\n',
    "    baseline_name: str | None = None,\n",
)
replace_once(
    statistics,
    "    baseline = by_name.get(baseline_name)\n"
    "    if baseline is None:\n"
    "        raise ValueError(\n"
    '            f"Baseline experiment {baseline_name!r} was not found."\n'
    "        )\n",
    "    resolved_baseline = resolve_baseline_name(run, baseline_name)\n"
    "    baseline = by_name[resolved_baseline]\n",
)
replace_once(
    statistics,
    "        if name == baseline_name:\n",
    "        if name == resolved_baseline:\n",
)

decision = root / "src/gridiron/research/decision.py"
replace_once(
    decision,
    "from gridiron.research.models import ResearchRun\n",
    "from gridiron.research.baseline import resolve_baseline_name\n"
    "from gridiron.research.models import ResearchRun\n",
)
replace_once(
    decision,
    '    baseline_name: str = "rest_000_baseline",\n',
    "    baseline_name: str | None = None,\n",
)
replace_once(
    decision,
    "    statistics = analyze_candidates(\n"
    "        run,\n"
    "        baseline_name=baseline_name,\n"
    "    )\n",
    "    resolved_baseline = resolve_baseline_name(run, baseline_name)\n"
    "    statistics = analyze_candidates(\n"
    "        run,\n"
    "        baseline_name=resolved_baseline,\n"
    "    )\n",
)
replace_once(
    decision,
    "        baseline=baseline_name,\n",
    "        baseline=resolved_baseline,\n",
)

print("62B baseline fixes applied.")
