from structured_retriever.retriever import StructuredRetriever
from literature_retriever.retriever import LiteratureRetriever
from biomedical_rag.rag_pipeline import RAGPipeline
from evidence_extractor.extractor import EvidenceExtractor
from evidence_graph.graph import EvidenceGraphBuilder
from evidence_fusion.fusion import EvidenceFusion


DISEASE_ID = "MONDO:0005148"
DISEASE_NAME = "type 2 diabetes mellitus"

TARGET_LIMIT = 3
PAPERS_PER_TARGET = 2


print("=" * 80)
print("EVIDENCE FUSION - FULL INTEGRATION TEST")
print("=" * 80)


# ---------------------------------------------------------
# STEP 1: Retrieve real targets from Open Targets
# ---------------------------------------------------------

print("\nRetrieving targets from Open Targets...")

structured_retriever = StructuredRetriever()

structured_result = structured_retriever.retrieve_targets(
    disease_id=DISEASE_ID,
    page_size=100,
    max_targets=500,
    min_score=0.60,
    top_n=TARGET_LIMIT
)

targets = structured_result.targets[:TARGET_LIMIT]

print(f"Total Open Targets associations: {structured_result.total_targets}")
print(f"Using targets: {len(targets)}")


# ---------------------------------------------------------
# STEP 2: Retrieve literature for those targets
# ---------------------------------------------------------

target_symbols = [
    target.symbol
    for target in targets
]

print("\nRetrieving literature...")

literature_retriever = LiteratureRetriever()

batch_result = literature_retriever.search_targets(
    disease_name=DISEASE_NAME,
    target_symbols=target_symbols,
    papers_per_target=PAPERS_PER_TARGET
)

print(f"Unique papers: {batch_result.total_papers}")


# ---------------------------------------------------------
# STEP 3: Build RAG
# ---------------------------------------------------------

print("\nBuilding RAG pipeline...")

rag = RAGPipeline()

rag.add_papers(
    papers=batch_result.papers,
    disease_name=DISEASE_NAME
)

print("RAG index built.")


# ---------------------------------------------------------
# STEP 4: Build Evidence Graph
# ---------------------------------------------------------

graph_builder = EvidenceGraphBuilder()

graph_builder.add_disease(
    disease_id=DISEASE_ID,
    disease_name=DISEASE_NAME
)


for target in targets:

    graph_builder.add_target(
        target_id=target.id,
        symbol=target.symbol,
        name=target.name
    )


extractor = EvidenceExtractor()


for target in targets:

    results = rag.search(
        query=f"{DISEASE_NAME} {target.symbol}",
        retrieval_k=10,
        final_k=5
    )

    for result in results:

        if result.chunk.pmid:

            graph_builder.add_paper(
                pmid=result.chunk.pmid,
                title=result.chunk.title
            )

        evidence_result = extractor.extract_from_chunk(
            chunk=result.chunk,
            disease_name=DISEASE_NAME,
            target_symbol=target.symbol
)

        graph_builder.add_extraction_result(
            evidence_result.evidence_items
        )


graph = graph_builder.build()


print("\nEvidence Graph:")
print(f"Diseases: {len(graph.diseases)}")
print(f"Targets: {len(graph.targets)}")
print(f"Papers: {len(graph.papers)}")
print(f"Evidence: {len(graph.evidence)}")
print(f"Edges: {len(graph.edges)}")


# ---------------------------------------------------------
# STEP 5: Evidence Fusion
# ---------------------------------------------------------

print("\nRunning Evidence Fusion...")

fusion = EvidenceFusion()


fusion_results = []


for target in targets:

    target_input = fusion.build_target_input(
        target_id=target.id,
        target_symbol=target.symbol,
        structured_score=target.score,
        evidence_graph=graph
    )

    result = fusion.fuse(target_input)

    fusion_results.append(result)


# ---------------------------------------------------------
# STEP 6: Sort by fused score
# ---------------------------------------------------------

fusion_results.sort(
    key=lambda result: result.fused_score,
    reverse=True
)


# ---------------------------------------------------------
# STEP 7: Display final ranking
# ---------------------------------------------------------

print("\n")
print("=" * 80)
print("FUSED TARGET RANKING")
print("=" * 80)


for rank, result in enumerate(
    fusion_results,
    start=1
):

    print(
        f"{rank}. {result.target_symbol}"
    )

    print(
        f"   Open Targets score: "
        f"{result.structured_score:.4f}"
    )

    print(
        f"   Evidence count: "
        f"{result.evidence_count}"
    )

    print(
        f"   Strong: "
        f"{result.strong_evidence_count}"
    )

    print(
        f"   Moderate: "
        f"{result.moderate_evidence_count}"
    )

    print(
        f"   Weak: "
        f"{result.weak_evidence_count}"
    )

    print(
        f"   Literature score: "
        f"{result.literature_score:.4f}"
    )

    print(
        f"   Fused score: "
        f"{result.fused_score:.4f}"
    )

    print("-" * 80)


print("\nFULL EVIDENCE FUSION INTEGRATION TEST COMPLETED")