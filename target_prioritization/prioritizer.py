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
            key=lambda result: result.fused_score,
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
                    fused_score=result.fused_score,
                    structured_score=result.structured_score,
                    literature_score=result.literature_score,
                    evidence_count=result.evidence_count,
                    literature_status=result.literature_status
                )
            )

        return TargetPrioritizationResult(
            total_targets=len(fusion_results),
            selected_targets=len(prioritized_targets),
            targets=prioritized_targets
        )
