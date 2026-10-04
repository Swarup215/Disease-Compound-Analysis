from typing import Optional

from pydantic import BaseModel, Field


class DiseaseNode(BaseModel):
    id: str
    name: str


class TargetNode(BaseModel):
    id: str
    symbol: str
    name: Optional[str] = None


class PaperNode(BaseModel):
    pmid: str
    title: Optional[str] = None


class EvidenceNode(BaseModel):
    id: str

    pmid: Optional[str] = None

    disease_name: str
    target_symbol: str

    evidence_text: str

    evidence_type: str

    relation: str

    evidence_strength: str

    direction: str

    confidence: float


class EvidenceEdge(BaseModel):
    source_id: str
    relation: str
    target_id: str


class EvidenceGraph(BaseModel):

    diseases: list[DiseaseNode] = Field(
        default_factory=list
    )

    targets: list[TargetNode] = Field(
        default_factory=list
    )

    papers: list[PaperNode] = Field(
        default_factory=list
    )

    evidence: list[EvidenceNode] = Field(
        default_factory=list
    )

    edges: list[EvidenceEdge] = Field(
        default_factory=list
    )