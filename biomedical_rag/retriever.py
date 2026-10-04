from biomedical_rag.embedder import TextEmbedder
from biomedical_rag.models import RAGChunk
from biomedical_rag.vector_store import VectorStore


class SemanticRetriever:

    def __init__(
        self,
        embedder: TextEmbedder,
        vector_store: VectorStore
    ):
        self.embedder = embedder
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> list[tuple[RAGChunk, float]]:

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty"
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0"
            )

        query_embedding = self.embedder.embed_text(
            query
        )

        return self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k
        )