from sentence_transformers import SentenceTransformer

from biomedical_rag.models import RAGDocument


class TextEmbedder:

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.model = SentenceTransformer(model_name)

    def embed_text(
        self,
        text: str
    ) -> list[float]:

        if not text or not text.strip():
            raise ValueError(
                "Text cannot be empty"
            )

        vector = self.model.encode(
            text,
            convert_to_numpy=True
        )

        return vector.tolist()

    def embed_documents(
        self,
        documents: list[RAGDocument]
    ) -> list[list[float]]:

        if not documents:
            return []

        texts = [
            document.text
            for document in documents
        ]

        vectors = self.model.encode(
            texts,
            convert_to_numpy=True
        )

        return vectors.tolist()