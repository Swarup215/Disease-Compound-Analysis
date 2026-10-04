from literature_retriever.models import Paper

from biomedical_rag.chunker import TextChunker
from biomedical_rag.document_processor import DocumentProcessor
from biomedical_rag.embedder import TextEmbedder
from biomedical_rag.models import RAGChunk, RerankedResult
from biomedical_rag.reranker import Reranker
from biomedical_rag.retriever import SemanticRetriever
from biomedical_rag.vector_store import VectorStore


class RAGPipeline:

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 100,
        embedding_model: str = "all-MiniLM-L6-v2",
        reranker_model: str = (
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
    ):
        self.document_processor = DocumentProcessor()

        self.chunker = TextChunker(
            chunk_size=chunk_size,
            overlap=overlap
        )

        self.embedder = TextEmbedder(
            model_name=embedding_model
        )

        self.reranker = Reranker(
            model_name=reranker_model
        )

        self.vector_store = VectorStore(
            dimension=384
        )

        self.retriever = SemanticRetriever(
            embedder=self.embedder,
            vector_store=self.vector_store
        )

    def add_papers(
        self,
        papers: list[Paper],
        disease_name: str | None = None,
    ) -> int:

        if not papers:
            return 0

        rag_chunks = []

        for paper in papers:

            document = (
                self.document_processor.paper_to_document(
                    paper=paper,
                    disease_name=disease_name,
                )
            )

            chunks = self.chunker.chunk_document(
                document
            )

            embeddings = self.embedder.embed_documents(
                chunks
            )

            for chunk, embedding in zip(
                chunks,
                embeddings
            ):
                rag_chunks.append(
                    RAGChunk(
                        chunk_id=chunk.document_id,
                        text=chunk.text,
                        embedding=embedding,
                        pmid=chunk.pmid,
                        title=chunk.title,
                        disease_name=chunk.disease_name,
                        target_symbols=chunk.target_symbols,
                        metadata=chunk.metadata
                    )
                )

        self.vector_store.add(
            rag_chunks
        )

        return len(rag_chunks)

    def search(
        self,
        query: str,
        retrieval_k: int = 10,
        final_k: int = 5
    ) -> list[RerankedResult]:

        retrieved = self.retriever.search(
            query=query,
            top_k=retrieval_k
        )

        return self.reranker.rerank(
            query=query,
            results=retrieved,
            top_k=final_k
        )