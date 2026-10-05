from evidence_fusion.models import TargetFusionResult
from target_prioritization.models import (
    PrioritizedTarget,
    TargetPrioritizationResult
)


class TargetPrioritizer:

    def prioritize(
        self,
        fusion_results: list[TargetFusionResult],
        top_n: int = 10
    ) -> TargetPrioritizationResult:

        if not fusion_results:
            raise ValueError("Fusion results cannot be empty")

        if top_n <= 0:
            raise ValueError("top_n must be greater than 0")

        sorted_results = sorted(
            fusion_results,
            key=lambda result: (
                result.fused_score,
                result.structured_score,
                result.evidence_count
            ),
            reverse=True
        )

        selected_results = sorted_results[:top_n]

        prioritized_targets = []

        for rank, result in enumerate(
            selected_results,
            start=1
        ):
            prioritized_targets.append(
                PrioritizedTarget(
                    rank=rank,
                    target_id=result.target_id,
                    target_symbol=result.target_symbol,
                    target_name=result.target_name,
                    fused_score=round(result.fused_score, 4),
                    structured_score=round(result.structured_score, 4),
                    literature_score=round(result.literature_score, 4),
                    evidence_count=result.evidence_count,
                    strong_evidence_count=result.strong_evidence_count,
                    moderate_evidence_count=result.moderate_evidence_count,
                    weak_evidence_count=result.weak_evidence_count,
                    negative_evidence_count=result.negative_evidence_count,
                    literature_status=result.literature_status,
                    evidence_items=result.evidence_items,
                    datatype_scores=result.datatype_scores,
                    papers_referenced=result.papers_referenced
                )
            )

        return TargetPrioritizationResult(
            total_targets=len(fusion_results),
            selected_targets=len(prioritized_targets),
            targets=prioritized_targets
        )
