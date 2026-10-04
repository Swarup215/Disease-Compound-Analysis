from typing import Dict, Optional

from pydantic import BaseModel, Field


class RAGDocument(BaseModel):
    document_id: str
    text: str

    pmid: Optional[str] = None
    title: Optional[str] = None

    disease_name: Optional[str] = None
    target_symbols: list[str] = Field(
        default_factory=list
    )

    metadata: Dict[str, str] = Field(
        default_factory=dict
    )


class RAGChunk(BaseModel):
    chunk_id: str
    text: str

    embedding: list[float]

    pmid: Optional[str] = None
    title: Optional[str] = None

    disease_name: Optional[str] = None
    target_symbols: list[str] = Field(
        default_factory=list
    )

    metadata: Dict[str, str] = Field(
        default_factory=dict
    )


class RerankedResult(BaseModel):
    chunk: RAGChunk
    score: float