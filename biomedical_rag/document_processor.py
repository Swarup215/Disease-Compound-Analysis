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

        paper_source = getattr(paper, "source", None) or "PubMed"
        paper_url = getattr(paper, "url", None) or (f"https://pubmed.ncbi.nlm.nih.gov/{paper.pmid}/" if paper.pmid else None)
        paper_pmcid = getattr(paper, "pmcid", None)
        paper_doi = getattr(paper, "doi", None)

        metadata = {
            "source": paper_source,
            "target_symbols": ",".join(paper.target_symbols)
        }
        if paper_url:
            metadata["url"] = paper_url
        if paper_pmcid:
            metadata["pmcid"] = paper_pmcid
        if paper_doi:
            metadata["doi"] = paper_doi

        return RAGDocument(
            document_id=f"{paper_source}:{paper.pmid}",
            text=text,
            pmid=paper.pmid,
            title=paper.title,
            disease_name=disease_name,
            target_symbols=paper.target_symbols,
            metadata=metadata
        )