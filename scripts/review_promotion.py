"""Generate a promotion decision from a fresh research run."""
from __future__ import annotations

import argparse
from pathlib import Path

from gridiron.core.paths import ProjectPaths
from gridiron.experiments.config import load_experiments
from gridiron.research.config import load_research_profiles
from gridiron.research.decision import build_promotion_decision
from gridiron.research.decision_registry import (
    append_promotion_history,
    write_promotion_decision,
)
from gridiron.research.decision_report import print_promotion_decision
from gridiron.research.runner import run_research


def build_parser()->argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description='Run multi-season research and generate a promotion decision.')
    parser.add_argument('--profile',default='modern'); parser.add_argument('--project-root',type=Path,default=Path('.')); parser.add_argument('--research-config',type=Path,default=None); parser.add_argument('--experiment-config',type=Path,default=None); return parser
def main()->int:
    args=build_parser().parse_args(); paths=ProjectPaths.from_root(args.project_root)
    research_config=args.research_config if args.research_config is not None else paths.root/'config'/'research.toml'
    experiment_config=args.experiment_config if args.experiment_config is not None else paths.root/'config'/'experiments.toml'
    profiles=load_research_profiles(research_config); experiments=load_experiments(experiment_config)
    run=run_research(profile=args.profile,seasons=profiles.seasons_for(args.profile),experiments=experiments,project_root=paths.root)
    decision=build_promotion_decision(run); promotion_dir=paths.root/'data'/'reports'/'promotions'
    current_path=write_promotion_decision(promotion_dir/'promotion_decision.json',decision)
    history_path=append_promotion_history(promotion_dir/'promotion_history.json',decision)
    print_promotion_decision(decision); print(f'Decision: {current_path}'); print(f'History:  {history_path}'); return 0
if __name__=='__main__': raise SystemExit(main())
