from typing import List, Optional

from pydantic import BaseModel, Field


class TargetEvidence(BaseModel):

    scores: dict[str, float] = Field(
        default_factory=dict
    )


class TargetCandidate(BaseModel):

    id: str

    symbol: Optional[str] = None

    name: Optional[str] = None

    score: float = 0.0

    evidence: TargetEvidence = Field(
        default_factory=TargetEvidence
    )

    source: str = "Open Targets"


class StructuredRetrievalResult(BaseModel):

    disease_id: str

    disease_name: Optional[str] = None

    total_targets: int = 0

    retrieved_targets: int = 0

    filtered_targets: int = 0

    targets: List[TargetCandidate] = Field(
        default_factory=list
    )