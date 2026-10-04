from evidence_fusion.models import (
    TargetFusionInput,
    TargetFusionResult
)


class EvidenceFusion:

    def __init__(
        self,
        structured_weight: float = 0.6,
        literature_weight: float = 0.4
    ):

        if structured_weight < 0:
            raise ValueError(
                "structured_weight cannot be negative"
            )

        if literature_weight < 0:
            raise ValueError(
                "literature_weight cannot be negative"
            )

        if structured_weight + literature_weight == 0:
            raise ValueError(
                "At least one weight must be greater than 0"
            )

        self.structured_weight = structured_weight
        self.literature_weight = literature_weight

    def build_target_input(
        self,
        target_id: str,
        target_symbol: str,
        structured_score: float,
        evidence_graph
    ) -> TargetFusionInput:

        target_evidence = [
            evidence
            for evidence in evidence_graph.evidence
            if evidence.target_symbol == target_symbol
        ]

        strong_count = sum(
            1
            for evidence in target_evidence
            if evidence.evidence_strength == "strong"
        )

        moderate_count = sum(
            1
            for evidence in target_evidence
            if evidence.evidence_strength == "moderate"
        )

        weak_count = sum(
            1
            for evidence in target_evidence
            if evidence.evidence_strength == "weak"
        )

        return TargetFusionInput(
            target_id=target_id,
            target_symbol=target_symbol,
            structured_score=structured_score,
            evidence_count=len(target_evidence),
            strong_evidence_count=strong_count,
            moderate_evidence_count=moderate_count,
            weak_evidence_count=weak_count
        )

    def calculate_literature_score(
        self,
        evidence: TargetFusionInput
    ) -> float:

        if evidence.evidence_count == 0:
            return 0.0

        weighted_evidence = (
            evidence.strong_evidence_count * 1.0
            + evidence.moderate_evidence_count * 0.6
            + evidence.weak_evidence_count * 0.3
        )

        score = (
            weighted_evidence
            / evidence.evidence_count
        )

        return min(score, 1.0)

    def fuse(
    self,
        evidence: TargetFusionInput
    ) -> TargetFusionResult:

        literature_score = (
            self.calculate_literature_score(evidence)
    )

        if evidence.evidence_count == 0:
            literature_status = "no_evidence"
        else:
            literature_status = "evidence_found"

        fused_score = (
            evidence.structured_score
            * self.structured_weight
            +
            literature_score
            * self.literature_weight
        )

        return TargetFusionResult(
            target_id=evidence.target_id,
            target_symbol=evidence.target_symbol,
            structured_score=evidence.structured_score,
            evidence_count=evidence.evidence_count,
            strong_evidence_count=evidence.strong_evidence_count,
            moderate_evidence_count=evidence.moderate_evidence_count,
            weak_evidence_count=evidence.weak_evidence_count,
            literature_score=literature_score,
            literature_status=literature_status,
            fused_score=fused_score
        )