from pydantic import BaseModel


class PrioritizedTarget(BaseModel):
    rank: int
    target_id: str
    target_symbol: str

    fused_score: float
    structured_score: float
    literature_score: float

    evidence_count: int
    literature_status: str


class TargetPrioritizationResult(BaseModel):
    total_targets: int
    selected_targets: int
    targets: list[PrioritizedTarget]
