from pydantic import BaseModel


class TargetFusionInput(BaseModel):
    target_id: str
    target_symbol: str

    structured_score: float = 0.0

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

    literature_status: str = "no_evidence"

    fused_score: float = 0.0