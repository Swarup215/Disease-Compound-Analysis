from structured_retriever import StructuredRetriever


def main():

    retriever = StructuredRetriever()

    disease_id = "MONDO:0005148"

    result = retriever.retrieve_targets(

        disease_id=disease_id,

        page_size=100,

        max_targets=500,

        min_score=0.60,

        top_n=50
    )

    print("\n")
    print("=" * 70)
    print("STRUCTURED TARGET RETRIEVAL")
    print("=" * 70)

    print(
        "Disease ID:",
        result.disease_id
    )

    print(
        "Disease:",
        result.disease_name
    )

    print(
        "Total associated targets:",
        result.total_targets
    )

    print(
        "Retrieved targets:",
        result.retrieved_targets
    )

    print(
        "Filtered targets:",
        result.filtered_targets
    )

    print("\nSelected targets:")

    for index, target in enumerate(
        result.targets,
        start=1
    ):

        print(
            f"{index:2}. "
            f"{target.symbol:10} | "
            f"{target.score:.4f} | "
            f"{target.id} | "
            f"{target.name}"
        )

        print(
    f"    Evidence: "
    f"{target.evidence.scores}"
)


if __name__ == "__main__":
    main()