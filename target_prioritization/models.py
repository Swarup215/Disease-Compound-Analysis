from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PrioritizedTarget(BaseModel):
    rank: int
    target_id: str
    target_symbol: str
    target_name: Optional[str] = None

    fused_score: float
    structured_score: float
    literature_score: float

    evidence_count: int
    strong_evidence_count: int = 0
    moderate_evidence_count: int = 0
    weak_evidence_count: int = 0
    negative_evidence_count: int = 0
    literature_status: str

    evidence_items: List[Any] = Field(default_factory=list)
    datatype_scores: Dict[str, float] = Field(default_factory=dict)
    papers_referenced: List[Dict[str, Any]] = Field(default_factory=list)


class TargetPrioritizationResult(BaseModel):
    total_targets: int
    selected_targets: int
    targets: List[PrioritizedTarget]
