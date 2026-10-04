import faiss
import numpy as np

from biomedical_rag.models import RAGChunk


class VectorStore:

    def __init__(self, dimension: int):
        if dimension <= 0:
            raise ValueError(
                "dimension must be greater than 0"
            )

        self.dimension = dimension

        self.index = faiss.IndexFlatL2(
            dimension
        )

        self.chunks: list[RAGChunk] = []

    def add(
        self,
        chunks: list[RAGChunk]
    ) -> None:

        if not chunks:
            return

        vectors = np.array(
            [chunk.embedding for chunk in chunks],
            dtype="float32"
        )

        if vectors.shape[1] != self.dimension:
            raise ValueError(
                "Embedding dimension does not match "
                "vector store dimension"
            )

        self.index.add(vectors)

        self.chunks.extend(chunks)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5
    ) -> list[tuple[RAGChunk, float]]:

        if not query_embedding:
            raise ValueError(
                "Query embedding cannot be empty"
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0"
            )

        if not self.chunks:
            return []

        query_vector = np.array(
            [query_embedding],
            dtype="float32"
        )

        distances, indices = self.index.search(
            query_vector,
            min(top_k, len(self.chunks))
        )

        results = []

        for distance, index in zip(
            distances[0],
            indices[0]
        ):
            if index < 0:
                continue

            results.append(
                (
                    self.chunks[index],
                    float(distance)
                )
            )

        return results

    def count(self) -> int:
        return len(self.chunks)