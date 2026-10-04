from typing import List, Optional
from pydantic import BaseModel, Field


class DiseaseInput(BaseModel):
    original: str


class DiseaseIdentifiers(BaseModel):
    mondo: Optional[str] = None
    doid: Optional[str] = None
    efo: Optional[str] = None
    mesh: Optional[str] = None


class DiseaseSynonyms(BaseModel):
    exact: List[str] = Field(default_factory=list)
    narrow: List[str] = Field(default_factory=list)
    broad: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)


class DiseaseCandidate(BaseModel):
    id: str
    label: str
    ontology: Optional[str] = None
    score: float = 0.0
    match_type: str = "unknown"
    synonyms: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class NormalizationMetadata(BaseModel):
    status: str
    match_type: Optional[str] = None
    score: float = 0.0
    source: Optional[str] = None


class DiseaseConcept(BaseModel):
    input: DiseaseInput

    canonical_name: Optional[str] = None
    canonical_id: Optional[str] = None

    identifiers: DiseaseIdentifiers = Field(
        default_factory=DiseaseIdentifiers
    )

    synonyms: DiseaseSynonyms = Field(
        default_factory=DiseaseSynonyms
    )

    cross_references: List[str] = Field(
        default_factory=list
    )

    definition: Optional[str] = None

    normalization: NormalizationMetadata

    candidates: List[DiseaseCandidate] = Field(
        default_factory=list
    )