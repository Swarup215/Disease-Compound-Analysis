from literature_retriever.models import Paper

from biomedical_rag.models import RAGDocument


class DocumentProcessor:

    @staticmethod
    def paper_to_document(
        paper: Paper,
        disease_name: str | None = None
    ) -> RAGDocument:

        title = paper.title.strip()

        abstract = ""

        if paper.abstract:
            abstract = paper.abstract.strip()

        if title and abstract:
            text = f"{title}\n\n{abstract}"

        elif title:
            text = title

        else:
            text = abstract

        return RAGDocument(
            document_id=f"PMID:{paper.pmid}",
            text=text,
            pmid=paper.pmid,
            title=paper.title,
            disease_name=disease_name,
            target_symbols=paper.target_symbols,
            metadata={
                "source": "PubMed",
                "target_symbols": ",".join(
                    paper.target_symbols
                )
            }
        )