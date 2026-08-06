"""Persistence for promotion decisions."""
from __future__ import annotations

import json
from pathlib import Path

from gridiron.research.decision import PromotionDecision


def write_promotion_decision(path:Path,decision:PromotionDecision)->Path:
    path.parent.mkdir(parents=True,exist_ok=True); temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8') as handle:
        json.dump(decision.to_dict(),handle,indent=2,sort_keys=True); handle.write('\n')
    temporary.replace(path); return path
def append_promotion_history(path:Path,decision:PromotionDecision)->Path:
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        with path.open(encoding='utf-8') as handle: payload=json.load(handle)
        if not isinstance(payload,list): raise TypeError('Promotion history must contain a JSON list.')
    else: payload=[]
    payload.append(decision.to_dict()); temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8') as handle:
        json.dump(payload,handle,indent=2,sort_keys=True); handle.write('\n')
    temporary.replace(path); return path
