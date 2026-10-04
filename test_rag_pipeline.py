from literature_retriever.retriever import LiteratureRetriever
from biomedical_rag.rag_pipeline import RAGPipeline


def main():

    disease_name = "type 2 diabetes mellitus"

    target_symbols = [
        "KCNJ11",
        "ABCC8",
        "GCK"
    ]

    print("Retrieving literature...")

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

    print("Building RAG pipeline...")

    pipeline = RAGPipeline(
        chunk_size=500,
        overlap=100
    )

    indexed_chunks = pipeline.add_papers(
        papers=batch_result.papers,
        disease_name=disease_name
    )

    print(
        "Indexed chunks:",
        indexed_chunks
    )

    print()

    query = (
        "What evidence connects the target "
        "to type 2 diabetes mellitus?"
    )

    print("Query:")
    print(query)

    print()

    results = pipeline.search(
        query=query,
        retrieval_k=10,
        final_k=5
    )

    print("Retrieved evidence:")
    print()

    for number, result in enumerate(
        results,
        start=1
    ):

        print(
            f"{number}. "
            f"PMID: {result.chunk.pmid}"
        )

        print(
            f"   Score: {result.score}"
        )

        print(
            f"   Target: "
            f"{result.chunk.target_symbols}"
        )

        print(
            f"   Text: "
            f"{result.chunk.text}"
        )

        print()


if __name__ == "__main__":
    main()