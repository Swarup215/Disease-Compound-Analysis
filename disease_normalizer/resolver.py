from typing import List

from .models import DiseaseCandidate
from .preprocess import normalize_for_matching


def get_candidate_texts(candidate: dict) -> List[str]:

    texts = []

    label = candidate.get("label")

    if label:
        texts.append(label)

    synonyms = candidate.get("synonym", [])

    if isinstance(synonyms, str):
        synonyms = [synonyms]

    texts.extend(synonyms)

    return texts


def score_candidate(
    query: str,
    candidate: dict
) -> DiseaseCandidate:

    query_normalized = normalize_for_matching(query)

    label = candidate.get("label") or ""

    label_normalized = normalize_for_matching(label)

    synonyms = get_candidate_texts(candidate)

    normalized_synonyms = [
        normalize_for_matching(x)
        for x in synonyms
        if x
    ]

    if query_normalized == label_normalized:
        score = 1.0
        match_type = "exact_label"

    elif query_normalized in normalized_synonyms:
        score = 0.95
        match_type = "exact_synonym"

    elif (
        query_normalized in label_normalized
        or label_normalized in query_normalized
    ):
        score = 0.85
        match_type = "partial_label"

    elif any(
        query_normalized in synonym
        or synonym in query_normalized
        for synonym in normalized_synonyms
    ):
        score = 0.80
        match_type = "partial_synonym"

    else:
        score = 0.0
        match_type = "no_match"

    # Safely extract description
    description_data = candidate.get("description")

    if isinstance(description_data, list):
        description = (
            description_data[0]
            if description_data
            else None
        )
    else:
        description = description_data

    return DiseaseCandidate(
        id=(
            candidate.get("obo_id")
            or candidate.get("short_form")
            or candidate.get("iri")
        ),
        label=label,
        ontology=candidate.get("ontology_name"),
        score=score,
        match_type=match_type,
        synonyms=(
            synonyms
            if isinstance(synonyms, list)
            else []
        ),
        description=description
    )