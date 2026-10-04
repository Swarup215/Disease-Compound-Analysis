from typing import Dict, List

from .models import (
    DiseaseConcept,
    DiseaseInput,
    DiseaseIdentifiers,
    DiseaseSynonyms,
    NormalizationMetadata,
)

from .preprocess import preprocess_disease_name
from .ols import OLSClient
from .resolver import score_candidate


SUPPORTED_ONTOLOGIES = [
    "mondo",
    "doid",
    "efo",
    "mesh",
]


class DiseaseNormalizer:

    def __init__(self):

        self.ols = OLSClient()

    def normalize(
        self,
        disease_name: str
    ) -> DiseaseConcept:

        cleaned_name = preprocess_disease_name(
            disease_name
        )

        if not cleaned_name:

            raise ValueError(
                "Disease name cannot be empty."
            )

        candidates = []

        # ---------------------------------
        # Search each ontology
        # ---------------------------------

        for ontology in SUPPORTED_ONTOLOGIES:

            results = self.ols.search(
                query=cleaned_name,
                ontology=ontology,
                rows=10
            )

            for result in results:

                candidate = score_candidate(
                    cleaned_name,
                    result
                )

                candidates.append(candidate)

        # ---------------------------------
        # Sort candidates
        # ---------------------------------

        candidates.sort(
            key=lambda x: x.score,
            reverse=True
        )

        # ---------------------------------
        # No candidates
        # ---------------------------------

        if not candidates:

            return DiseaseConcept(
                input=DiseaseInput(
                    original=disease_name
                ),
                normalization=NormalizationMetadata(
                    status="no_match",
                    score=0.0,
                    source="OLS"
                )
            )

        best = candidates[0]

        # ---------------------------------
        # Determine status
        # ---------------------------------

        if best.match_type in (
        "exact_label",
        "exact_synonym"
    ):
            status = "resolved"

        elif best.match_type in (
            "partial_label",
        "partial_synonym"
    ):
            status = "ambiguous"

        else:
            status = "no_match"

        # ---------------------------------
        # Build identifiers
        # ---------------------------------

        identifiers = self._build_identifiers(
            candidates,
            best
        )

        # ---------------------------------
        # Build synonyms
        # ---------------------------------

        synonyms = self._build_synonyms(
            candidates,
            cleaned_name
        )

        return DiseaseConcept(
    input=DiseaseInput(
        original=disease_name
    ),

    canonical_name=(
        best.label
        if status == "resolved"
        else None
    ),

    canonical_id=(
        best.id
        if status == "resolved"
        else None
    ),

    identifiers=(
        identifiers
        if status == "resolved"
        else DiseaseIdentifiers()
    ),

    synonyms=synonyms,

    normalization=NormalizationMetadata(
        status=status,
        match_type=best.match_type,
        score=best.score,
        source="OLS"
    ),

    candidates=candidates[:10]
)

    def _build_identifiers(
        self,
        candidates,
        best_candidate
    ) -> DiseaseIdentifiers:

        identifiers = DiseaseIdentifiers()

        # Keep the best candidate found for each ontology
        best_by_ontology = {}

        for candidate in candidates:

            ontology = (
                candidate.ontology or ""
            ).lower()

            if ontology not in SUPPORTED_ONTOLOGIES:
                continue

            if ontology not in best_by_ontology:
                best_by_ontology[ontology] = candidate

            elif candidate.score > best_by_ontology[ontology].score:
                best_by_ontology[ontology] = candidate

        # Extract identifiers
        for ontology, candidate in best_by_ontology.items():

            candidate_id = candidate.id

            if not candidate_id:
                continue

            if ontology == "mondo":
                identifiers.mondo = candidate_id

            elif ontology == "doid":
                identifiers.doid = candidate_id

            elif ontology == "efo":
                identifiers.efo = candidate_id

            elif ontology == "mesh":
                identifiers.mesh = candidate_id

        return identifiers


    def _build_synonyms(
        self,
        candidates,
        query: str
    ) -> DiseaseSynonyms:

        exact = []
        related = []

        for candidate in candidates:

            for synonym in candidate.synonyms:

                if not synonym:
                    continue

                if (
                    preprocess_disease_name(
                        synonym
                    )
                    == query
                ):
                    exact.append(synonym)

                else:
                    related.append(synonym)

        return DiseaseSynonyms(
            exact=list(set(exact)),
            related=list(set(related))
        )