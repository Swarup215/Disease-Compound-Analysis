from typing import List, Optional

from pydantic import BaseModel, Field


class Paper(BaseModel):
    pmid: str
    title: str
    abstract: Optional[str] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    authors: List[str] = Field(
        default_factory=list
    )

    target_symbols: List[str] = Field(
        default_factory=list
    )
    source: str = "PubMed"
    url: Optional[str] = None
    pmcid: Optional[str] = None


class LiteratureRetrievalResult(BaseModel):
    query: str
    total_found: int = 0
    retrieved_papers: int = 0
    sources: List[str] = Field(
        default_factory=list
    )
    papers: List[Paper] = Field(
        default_factory=list
    )


class TargetLiteratureResult(BaseModel):
    disease_name: str
    target_symbol: str
    query: str
    total_found: int = 0
    retrieved_papers: int = 0
    sources: List[str] = Field(
        default_factory=list
    )
    papers: List[Paper] = Field(
        default_factory=list
    )


class BatchLiteratureResult(BaseModel):
    disease_name: str
    total_targets: int = 0
    processed_targets: int = 0
    total_papers: int = 0
    sources: List[str] = Field(
        default_factory=list
    )
    papers: List[Paper] = Field(
        default_factory=list
    )
    target_results: List[TargetLiteratureResult] = Field(
        default_factory=list
    )
