"""Console reporting for promotion decisions."""
from __future__ import annotations

from gridiron.research.decision import PromotionDecision


def format_promotion_decision(decision:PromotionDecision)->str:
    lines=['='*96,'PROJECT GRIDIRON PROMOTION DECISION'.center(96),'='*96,f'Profile................... {decision.profile}',f'Baseline.................. {decision.baseline}','-'*96,'Rank  Candidate          Status         W-L-T  Mean Delta  95% CI                  Acc Delta','-'*96]
    for c in decision.candidates:
        lines.append(f'{c.rank:>4}  {c.name:<18}{c.status.value:<15}{c.wins}-{c.losses}-{c.ties:<5}{c.mean_score_delta:>10.4f}  [{c.confidence_interval_low:>7.4f}, {c.confidence_interval_high:>7.4f}]{c.mean_accuracy_delta:>11.1%}')
    recommended=decision.recommended_candidate if decision.recommended_candidate is not None else 'None'
    lines.extend(['-'*96,f'Recommendation............ {decision.recommendation.value}',f'Recommended candidate..... {recommended}',f"Human approval required... {'YES' if decision.approval_required else 'NO'}",f'Reason.................... {decision.reason}','='*96])
    return '\n'.join(lines)
def print_promotion_decision(decision:PromotionDecision)->None: print(format_promotion_decision(decision))
