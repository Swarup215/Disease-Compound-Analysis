from pydantic import BaseModel, Field


class TargetFusionInput(BaseModel):
    target_id: str
    target_symbol: str

    # Score from Open Targets
    structured_score: float = 0.0

    # Literature evidence information
    evidence_count: int = 0
    strong_evidence_count: int = 0
    moderate_evidence_count: int = 0
    weak_evidence_count: int = 0


class TargetFusionResult(BaseModel):
    target_id: str
    target_symbol: str

    structured_score: float = 0.0

    evidence_count: int = 0
    strong_evidence_count: int = 0
    moderate_evidence_count: int = 0
    weak_evidence_count: int = 0

    literature_score: float = 0.0
    fused_score: float = 0.0