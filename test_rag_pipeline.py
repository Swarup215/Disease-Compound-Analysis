from literature_retriever.retriever import LiteratureRetriever
from biomedical_rag.rag_pipeline import RAGPipeline


def main():

    # =========================================================
    # Step 1: Define disease and targets
    # =========================================================

    disease_name = "type 2 diabetes mellitus"

    target_symbols = [
        "KCNJ11",
        "ABCC8",
        "GCK"
    ]

    # =========================================================
    # Step 2: Retrieve literature
    # =========================================================

    print("Retrieving literature...")
    print()

    literature_retriever = LiteratureRetriever()

    batch_result = literature_retriever.search_targets(
        disease_name=disease_name,
        target_symbols=target_symbols,
        papers_per_target=2
    )

    print(
        "Unique papers retrieved:",
        batch_result.total_papers
    )

    print()

    # =========================================================
    # Step 3: Show target-paper relationships
    # =========================================================

    print("Target-paper relationships:")
    print()

    for paper in batch_result.papers:

        print(
            f"PMID: {paper.pmid}"
        )

        print(
            f"Title: {paper.title}"
        )

        print(
            f"Targets: {paper.target_symbols}"
        )

        print()

    # =========================================================
    # Step 4: Build RAG pipeline
    # =========================================================

    print("Building RAG pipeline...")
    print()

    pipeline = RAGPipeline(
        chunk_size=500,
        overlap=100
    )

    # =========================================================
    # Step 5: Convert papers into chunks and embeddings
    # =========================================================

    indexed_chunks = pipeline.add_papers(
        papers=batch_result.papers,
        disease_name=disease_name
    )

    print(
        "Indexed chunks:",
        indexed_chunks
    )

    print()

    # =========================================================
    # Step 6: Target-specific semantic retrieval
    # =========================================================

    print("Target-specific evidence retrieval:")
    print()

    for target in target_symbols:

        query = (
            f"What evidence connects "
            f"{target} with "
            f"{disease_name}?"
        )

        print("=" * 80)
        print(f"Target: {target}")
        print(f"Query: {query}")
        print("=" * 80)
        print()

        # -----------------------------------------------------
        # Retrieve candidate chunks
        # -----------------------------------------------------

        results = pipeline.search(
            query=query,
            retrieval_k=10,
            final_k=5
        )

        # -----------------------------------------------------
        # Display results
        # -----------------------------------------------------

        if not results:

            print("No relevant evidence found.")
            print()

            continue

        for number, result in enumerate(
            results,
            start=1
        ):

            print(
                f"{number}. PMID: "
                f"{result.chunk.pmid}"
            )

            print(
                f"   Score: "
                f"{result.score}"
            )

            print(
                f"   Targets: "
                f"{result.chunk.target_symbols}"
            )

            print(
                f"   Title: "
                f"{result.chunk.title}"
            )

            print(
                f"   Text: "
                f"{result.chunk.text}"
            )

            print()

    # =========================================================
    # Step 7: Finish
    # =========================================================

    print("=" * 80)
    print("RAG test completed successfully.")
    print("=" * 80)


if __name__ == "__main__":
    main()