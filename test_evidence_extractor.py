from literature_retriever.retriever import LiteratureRetriever
from biomedical_rag.rag_pipeline import RAGPipeline
from evidence_extractor.extractor import EvidenceExtractor
from biomedical_rag.models import RAGChunk


def paper_to_full_chunk(paper, disease_name):
    """
    Convert the complete paper into one RAGChunk.

    Unlike the normal RAG chunks, this contains the
    complete title + abstract.
    """

    title = paper.title.strip() if paper.title else ""
    abstract = paper.abstract.strip() if paper.abstract else ""

    if title and abstract:
        text = f"{title}\n\n{abstract}"
    elif title:
        text = title
    else:
        text = abstract

    return RAGChunk(
        chunk_id=f"PMID:{paper.pmid}:full",
        text=text,
        embedding=[],
        pmid=paper.pmid,
        title=paper.title,
        disease_name=disease_name,
        target_symbols=paper.target_symbols,
        metadata={
            "source": "PubMed",
            "target_symbols": ",".join(
                paper.target_symbols
            ),
            "document_scope": "full_paper_abstract"
        }
    )


def main():

    disease_name = "type 2 diabetes mellitus"

    target_symbols = [
        "KCNJ11",
        "ABCC8",
        "GCK"
    ]

    # ---------------------------------------------------------
    # 1. Retrieve literature
    # ---------------------------------------------------------

    print("Retrieving literature...")

    literature_retriever = LiteratureRetriever()

    batch_result = literature_retriever.search_targets(
        disease_name=disease_name,
        target_symbols=target_symbols,
        papers_per_target=2
    )

    print(
        "Unique papers:",
        batch_result.total_papers
    )

    print()

    # ---------------------------------------------------------
    # 2. Build RAG
    # ---------------------------------------------------------

    print("Building RAG pipeline...")

    pipeline = RAGPipeline(
        chunk_size=500,
        overlap=100
    )

    pipeline.add_papers(
        papers=batch_result.papers,
        disease_name=disease_name
    )

    print("RAG index built.")
    print()

    # ---------------------------------------------------------
    # 3. Evidence extractor
    # ---------------------------------------------------------

    extractor = EvidenceExtractor(
        min_confidence=0.5,
        context_sentences=1
    )

    # ---------------------------------------------------------
    # 4. Process each target
    # ---------------------------------------------------------

    for target in target_symbols:

        print("=" * 80)
        print(f"TARGET: {target}")
        print("=" * 80)

        # -----------------------------------------------------
        # RAG retrieval
        # -----------------------------------------------------

        query = (
            f"What evidence connects "
            f"{target} with "
            f"{disease_name}?"
        )

        print()
        print("Query:")
        print(query)
        print()

        results = pipeline.search(
            query=query,
            retrieval_k=10,
            final_k=5
        )

        print(
            f"RAG returned {len(results)} chunks."
        )

        print()

        # -----------------------------------------------------
        # Find the papers represented by the RAG results
        # -----------------------------------------------------

        pmids = []

        for result in results:

            pmid = result.chunk.pmid

            if pmid and pmid not in pmids:
                pmids.append(pmid)

        print("Papers selected by RAG:")

        for pmid in pmids:
            print(f"  PMID: {pmid}")

        print()

        # -----------------------------------------------------
        # Evidence extraction from COMPLETE papers
        # -----------------------------------------------------

        total_evidence = 0

        for pmid in pmids:

            paper = next(
                (
                    p
                    for p in batch_result.papers
                    if p.pmid == pmid
                ),
                None
            )

            if paper is None:
                print(
                    f"Could not find paper "
                    f"for PMID {pmid}"
                )
                continue

            full_chunk = paper_to_full_chunk(
                paper=paper,
                disease_name=disease_name
            )

            extraction = extractor.extract_from_chunk(
                chunk=full_chunk,
                disease_name=disease_name,
                target_symbol=target
            )

            print("-" * 80)
            print(f"PMID: {pmid}")
            print(f"Title: {paper.title}")
            print()

            if not extraction.evidence_items:

                print("Evidence: NONE")

            else:

                for evidence in extraction.evidence_items:

                    total_evidence += 1

                    print(
                        "Evidence:",
                        evidence.evidence_text
                    )

                    print(
                        "Type:",
                        evidence.evidence_type
                    )
                    print(
                        "Relation:",
                        evidence.relation
                    )

                    print(
                        "Strength:",
                        evidence.evidence_strength
                    )

                    print(
                        "Direction:",
                        evidence.direction
                    )

                    print(
                        "Confidence:",
                        evidence.confidence
                    )

                    print()

        print()
        print(
            f"TOTAL EVIDENCE ITEMS: "
            f"{total_evidence}"
        )

        print()

    print("=" * 80)
    print("FULL-PAPER EVIDENCE TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()