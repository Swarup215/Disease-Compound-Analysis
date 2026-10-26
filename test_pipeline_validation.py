from types import SimpleNamespace

import pytest

from disease_normalizer.models import (
    DiseaseConcept,
    DiseaseIdentifiers,
    DiseaseInput,
    DiseaseSynonyms,
    NormalizationMetadata,
)
from pipeline import BiomedicalPipeline


class FakeNormalizer:
    def __init__(self, concept):
        self.concept = concept

    def normalize(self, disease_query):
        return self.concept


class FailingStructuredRetriever:
    def retrieve_targets(self, **kwargs):
        raise AssertionError("Open Targets must not run for an unresolved disease")


def disease_concept(status, canonical_id=None, canonical_name=None):
    return DiseaseConcept(
        input=DiseaseInput(original="not a real disease"),
        canonical_name=canonical_name,
        canonical_id=canonical_id,
        identifiers=DiseaseIdentifiers(),
        synonyms=DiseaseSynonyms(),
        normalization=NormalizationMetadata(
            status=status,
            score=1.0 if status == "resolved" else 0.0,
            source="OLS",
        ),
    )


def test_unresolved_disease_stops_before_open_targets():
    pipeline = BiomedicalPipeline.__new__(BiomedicalPipeline)
    pipeline.normalizer = FakeNormalizer(disease_concept("no_match"))
    pipeline.structured_retriever = FailingStructuredRetriever()

    with pytest.raises(ValueError, match="type the disease name again"):
        pipeline.run("not a real disease")


def test_partial_disease_stops_before_open_targets():
    pipeline = BiomedicalPipeline.__new__(BiomedicalPipeline)
    pipeline.normalizer = FakeNormalizer(
        disease_concept(
            "ambiguous",
            canonical_name=None,
        )
    )
    pipeline.structured_retriever = FailingStructuredRetriever()

    with pytest.raises(ValueError, match="type the disease name again"):
        pipeline.run("diabetes")


def test_resolved_disease_uses_only_resolved_ids():
    calls = []

    class EmptyStructuredRetriever:
        def retrieve_targets(self, **kwargs):
            calls.append(kwargs["disease_id"])
            return SimpleNamespace(targets=[])

    pipeline = BiomedicalPipeline.__new__(BiomedicalPipeline)
    pipeline.normalizer = FakeNormalizer(
        disease_concept(
            "resolved",
            canonical_id="MONDO:0005148",
            canonical_name="Type 2 diabetes mellitus",
        )
    )
    pipeline.structured_retriever = EmptyStructuredRetriever()

    with pytest.raises(ValueError, match="Could not find valid disease"):
        pipeline.run("Type 2 diabetes mellitus")

    assert calls == ["MONDO:0005148"]
