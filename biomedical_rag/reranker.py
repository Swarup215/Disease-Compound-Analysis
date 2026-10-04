from sentence_transformers import CrossEncoder

from biomedical_rag.models import (
    RAGChunk,
    RerankedResult
)


class Reranker:

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        results: list[tuple[RAGChunk, float]],
        top_k: int = 5
    ) -> list[RerankedResult]:

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty"
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0"
            )

        if not results:
            return []

        pairs = [
            (query, chunk.text)
            for chunk, _ in results
        ]

        scores = self.model.predict(pairs)

        reranked = []

        for (chunk, _), score in zip(
            results,
            scores
        ):
            reranked.append(
                RerankedResult(
                    chunk=chunk,
                    score=float(score)
                )
            )

        reranked.sort(
            key=lambda item: item.score,
            reverse=True
        )

        return reranked[:top_k]