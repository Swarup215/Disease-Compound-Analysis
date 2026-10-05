from typing import Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    pmid: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    authors: list[str] = Field(default_factory=list)

    disease_name: str
    target_symbol: str
    evidence_text: str

    evidence_type: str = "unknown"
    relation: str = "mentions"
    evidence_strength: str = "weak"
    direction: str = "unknown"
    confidence: float = 0.0
    source: str = "PubMed"


class EvidenceExtractionResult(BaseModel):
    target_symbol: str

    disease_name: str

    evidence_items: list[EvidenceItem] = Field(
        default_factory=list
    )