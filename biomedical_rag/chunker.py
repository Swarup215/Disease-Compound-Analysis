from biomedical_rag.models import RAGDocument


class TextChunker:

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 100
    ):
        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than 0"
            )

        if overlap < 0:
            raise ValueError(
                "overlap cannot be negative"
            )

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size"
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(
        self,
        document: RAGDocument
    ) -> list[RAGDocument]:

        text = document.text.strip()

        if not text:
            return []

        chunks = []

        start = 0
        chunk_number = 0

        while start < len(text):

            end = start + self.chunk_size

            chunk_text = text[start:end]

            chunks.append(
                RAGDocument(
                    document_id=(
                        f"{document.document_id}"
                        f":chunk:{chunk_number}"
                    ),
                    text=chunk_text,
                    pmid=document.pmid,
                    title=document.title,
                    disease_name=document.disease_name,
                    target_symbols=document.target_symbols,
                    metadata={
                        **document.metadata,
                        "chunk_number": str(
                            chunk_number
                        )
                    }
                )
            )

            chunk_number += 1

            if end >= len(text):
                break

            start = end - self.overlap

        return chunks