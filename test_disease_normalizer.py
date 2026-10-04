from disease_normalizer import DiseaseNormalizer


def test_disease(normalizer, disease):

    print("\n")
    print("=" * 60)
    print(f"TEST: {disease}")
    print("=" * 60)

    try:

        result = normalizer.normalize(disease)

        print(
            "Input:",
            result.input.original
        )

        print(
        "Canonical:",
        result.canonical_name or "NONE — ambiguous input"
            )

        print(
    "Canonical ID:",
    result.canonical_id or "NONE"
)

        print(
            "Status:",
            result.normalization.status
        )

        print(
            "Match:",
            result.normalization.match_type
        )

        print(
            "Score:",
            result.normalization.score
        )

        print("\nIdentifiers:")

        print(
            "MONDO:",
            result.identifiers.mondo
        )

        print(
            "DOID:",
            result.identifiers.doid
        )

        print(
            "EFO:",
            result.identifiers.efo
        )

        print(
            "MeSH:",
            result.identifiers.mesh
        )

        print("\nTop candidates:")

        for candidate in result.candidates[:5]:

            print(
                f"{candidate.score:.2f} | "
                f"{candidate.ontology} | "
                f"{candidate.id} | "
                f"{candidate.label} | "
                f"{candidate.match_type}"
            )

    except Exception as exc:

        print(
            "ERROR:",
            type(exc).__name__,
            str(exc)
        )


def main():

    normalizer = DiseaseNormalizer()

    diseases = [
        "Type 2 diabetes",
        "Alzheimer",
        "diabetes",
        "Intervertebral Disc Disease",
    ]

    for disease in diseases:

        test_disease(
            normalizer,
            disease
        )


if __name__ == "__main__":
    main()