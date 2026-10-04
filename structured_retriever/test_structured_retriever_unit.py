from structured_retriever.model import (
    TargetCandidate,
    TargetEvidence
)

from structured_retriever.retriever import (
    StructuredRetriever
)


def test_target_candidate():

    target = TargetCandidate(
        id="ENSG00000187486",
        symbol="KCNJ11",
        name="potassium inwardly rectifying channel",
        score=0.8772
    )

    assert target.id == "ENSG00000187486"
    assert target.symbol == "KCNJ11"
    assert target.score == 0.8772


def test_evidence_model():

    evidence = TargetEvidence(
        scores={
            "literature": 0.9,
            "genetic_association": 0.8
        }
    )

    assert evidence.scores["literature"] == 0.9
    assert evidence.scores["genetic_association"] == 0.8


def test_deduplication():

    targets = [

        TargetCandidate(
            id="ENSG001",
            symbol="GENE1",
            score=0.5
        ),

        TargetCandidate(
            id="ENSG001",
            symbol="GENE1",
            score=0.8
        ),

        TargetCandidate(
            id="ENSG002",
            symbol="GENE2",
            score=0.7
        )
    ]

    unique = (
        StructuredRetriever
        ._deduplicate_targets(
            targets
        )
    )

    assert len(unique) == 2

    gene1 = next(
        target
        for target in unique
        if target.id == "ENSG001"
    )

    assert gene1.score == 0.8


def test_evidence_parser():

    datatype_scores = [

        {
            "id": "genetic_association",
            "score": 0.91
        },

        {
            "id": "literature",
            "score": 0.72
        },

        {
            "id": "clinical",
            "score": 0.61
        },

        {
            "id": "animal_model",
            "score": 0.55
        }
    ]

    evidence = (
        StructuredRetriever
        ._parse_evidence(
            datatype_scores
        )
    )

    assert evidence.scores[
        "genetic_association"
    ] == 0.91

    assert evidence.scores[
        "literature"
    ] == 0.72

    assert evidence.scores[
        "clinical"
    ] == 0.61

    assert evidence.scores[
        "animal_model"
    ] == 0.55


def test_score_filter():

    targets = [

        TargetCandidate(
            id="A",
            score=0.90
        ),

        TargetCandidate(
            id="B",
            score=0.70
        ),

        TargetCandidate(
            id="C",
            score=0.50
        )
    ]

    filtered = [

        target

        for target in targets

        if target.score >= 0.60
    ]

    assert len(filtered) == 2


def test_top_n():

    targets = [

        TargetCandidate(
            id="A",
            score=0.90
        ),

        TargetCandidate(
            id="B",
            score=0.80
        ),

        TargetCandidate(
            id="C",
            score=0.70
        )
    ]

    targets.sort(
        key=lambda target: target.score,
        reverse=True
    )

    selected = targets[:2]

    assert len(selected) == 2

    assert selected[0].id == "A"
    assert selected[1].id == "B"