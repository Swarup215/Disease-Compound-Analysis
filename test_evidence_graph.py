from literature_retriever.retriever import LiteratureRetriever
from biomedical_rag.rag_pipeline import RAGPipeline
from evidence_extractor.extractor import EvidenceExtractor
from biomedical_rag.models import RAGChunk

from evidence_graph import EvidenceGraphBuilder


def paper_to_full_chunk(paper, disease_name):

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

    disease_id = "MONDO:0005148"

    target_symbols = [
        "KCNJ11",
        "ABCC8",
        "GCK"
    ]

    target_ids = {
        "KCNJ11": "ENSG00000187486",
        "ABCC8": "ENSG00000006071",
        "GCK": "ENSG00000106633"
    }

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
    # 4. Evidence graph
    # ---------------------------------------------------------

    graph_builder = EvidenceGraphBuilder()

    graph_builder.add_disease(
        disease_id=disease_id,
        disease_name=disease_name
    )

    for target in target_symbols:

        graph_builder.add_target(
            target_id=target_ids[target],
            symbol=target
        )

    # ---------------------------------------------------------
    # 5. Extract evidence
    # ---------------------------------------------------------

    for target in target_symbols:

        print("=" * 80)
        print(f"TARGET: {target}")
        print("=" * 80)

        query = (
            f"What evidence connects "
            f"{target} with "
            f"{disease_name}?"
        )

        results = pipeline.search(
            query=query,
            retrieval_k=10,
            final_k=5
        )

        pmids = []

        for result in results:

            pmid = result.chunk.pmid

            if pmid and pmid not in pmids:
                pmids.append(pmid)

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
                continue

            # Add paper to graph
            graph_builder.add_paper(
                pmid=paper.pmid,
                title=paper.title
            )

            # Convert complete paper to RAGChunk
            full_chunk = paper_to_full_chunk(
                paper=paper,
                disease_name=disease_name
            )

            # Extract evidence
            extraction = extractor.extract_from_chunk(
                chunk=full_chunk,
                disease_name=disease_name,
                target_symbol=target
            )

            # Add evidence to graph
            graph_builder.add_extraction_result(
                extraction.evidence_items
            )

    # ---------------------------------------------------------
    # 6. Build graph
    # ---------------------------------------------------------

    graph = graph_builder.build()

    # ---------------------------------------------------------
    # 7. Print graph summary
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("EVIDENCE GRAPH")
    print("=" * 80)

    print()
    print("Diseases:", len(graph.diseases))
    print("Targets:", len(graph.targets))
    print("Papers:", len(graph.papers))
    print("Evidence:", len(graph.evidence))
    print("Edges:", len(graph.edges))

    print()
    print("GRAPH EDGES")

    for edge in graph.edges:

        print(
        f"  {edge.source_id}"
        f" --[{edge.relation}]--> "
        f"{edge.target_id}"
    )

    # ---------------------------------------------------------
    # Disease nodes
    # ---------------------------------------------------------

    print("DISEASE NODES")

    for disease in graph.diseases:

        print(
            f"  {disease.id} | "
            f"{disease.name}"
        )

    print()

    # ---------------------------------------------------------
    # Target nodes
    # ---------------------------------------------------------

    print("TARGET NODES")

    for target in graph.targets:

        print(
            f"  {target.id} | "
            f"{target.symbol}"
        )

    print()

    # ---------------------------------------------------------
    # Evidence nodes
    # ---------------------------------------------------------

    print("EVIDENCE NODES")

    for evidence in graph.evidence:

        print("-" * 80)

        print(
            f"PMID: {evidence.pmid}"
        )

        print(
            f"Target: {evidence.target_symbol}"
        )

        print(
            f"Type: {evidence.evidence_type}"
        )

        print(
            f"Relation: {evidence.relation}"
        )

        print(
            f"Strength: {evidence.evidence_strength}"
        )

        print(
            f"Direction: {evidence.direction}"
        )

        print(
            f"Confidence: {evidence.confidence}"
        )

        print(
            f"Evidence: {evidence.evidence_text}"
        )

    print()

    print("=" * 80)
    print("EVIDENCE GRAPH TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()