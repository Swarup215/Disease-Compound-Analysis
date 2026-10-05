from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TargetFusionInput(BaseModel):
    target_id: str
    target_symbol: str
    target_name: Optional[str] = None

    structured_score: float = 0.0

    evidence_count: int = 0
    strong_evidence_count: int = 0
    moderate_evidence_count: int = 0
    weak_evidence_count: int = 0
    negative_evidence_count: int = 0

    evidence_items: List[Any] = Field(default_factory=list)
    datatype_scores: Dict[str, float] = Field(default_factory=dict)


class TargetFusionResult(BaseModel):
    target_id: str
    target_symbol: str
    target_name: Optional[str] = None

    structured_score: float = 0.0

    evidence_count: int = 0
    strong_evidence_count: int = 0
    moderate_evidence_count: int = 0
    weak_evidence_count: int = 0
    negative_evidence_count: int = 0

    literature_score: float = 0.0
    literature_status: str = "no_evidence"
    fused_score: float = 0.0

    evidence_items: List[Any] = Field(default_factory=list)
    datatype_scores: Dict[str, float] = Field(default_factory=dict)
    papers_referenced: List[Dict[str, Any]] = Field(default_factory=list)