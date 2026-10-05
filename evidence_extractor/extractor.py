import re

from biomedical_rag.models import RAGChunk

from evidence_extractor.models import (
    EvidenceItem,
    EvidenceExtractionResult
)

from evidence_extractor.rules import (
    contains_disease,
    contains_target,
    classify_direction,
    classify_evidence_type,
    classify_relation,
    classify_evidence_strength
)


class EvidenceExtractor:

    def __init__(
        self,
        min_confidence: float = 0.5,
        context_sentences: int = 1
    ):

        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError(
                "min_confidence must be between 0 and 1"
            )

        if context_sentences < 0:
            raise ValueError(
                "context_sentences cannot be negative"
            )

        self.min_confidence = min_confidence
        self.context_sentences = context_sentences

    def extract_from_chunk(
        self,
        chunk: RAGChunk,
        disease_name: str,
        target_symbol: str,
        synonyms: list[str] | None = None,
        paper_meta: dict | None = None
    ) -> EvidenceExtractionResult:

        if not disease_name or not disease_name.strip():
            raise ValueError(
                "Disease name cannot be empty"
            )

        if not target_symbol or not target_symbol.strip():
            raise ValueError(
                "Target symbol cannot be empty"
            )

        text = chunk.text.strip()

        if not text:
            return EvidenceExtractionResult(
                target_symbol=target_symbol,
                disease_name=disease_name,
                evidence_items=[]
            )

        sentences = self._split_sentences(text)

        evidence_items = []

        # Extract paper metadata if available
        meta = paper_meta or {}
        title = chunk.title or meta.get("title") or chunk.metadata.get("title")
        journal = meta.get("journal") or chunk.metadata.get("journal")
        pub_date = meta.get("publication_date") or chunk.metadata.get("publication_date")
        doi = meta.get("doi") or chunk.metadata.get("doi")
        authors = meta.get("authors") or []
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(",") if a.strip()]

        for index, sentence in enumerate(sentences):

            # Target must actually appear in the sentence
            if not contains_target(
                sentence,
                target_symbol
            ):
                continue

            context = self._build_context(
                sentences=sentences,
                target_index=index
            )

            disease_found = contains_disease(
                context,
                disease_name,
                synonyms=synonyms
            )

            # We need disease context for direct evidence.
            if not disease_found:
                # Also check title or chunk disease_name context
                if (chunk.title and contains_disease(chunk.title, disease_name, synonyms)) or \
                   (chunk.disease_name and contains_disease(chunk.disease_name, disease_name, synonyms)):
                    disease_found = True

            if not disease_found:
                continue

            evidence_type = classify_evidence_type(
                context
            )

            relation = classify_relation(
                text=context,
                target_symbol=target_symbol,
                disease_name=disease_name,
                synonyms=synonyms
            )

            evidence_strength = classify_evidence_strength(
                evidence_type=evidence_type,
                relation=relation
            )

            direction = classify_direction(
                text=context,
                relation=relation
            )

            confidence = self._calculate_confidence(
                context=context,
                target_symbol=target_symbol,
                disease_name=disease_name,
                evidence_type=evidence_type,
                relation=relation,
                direction=direction,
                synonyms=synonyms
            )

            if confidence < self.min_confidence:
                continue

            evidence_items.append(
                EvidenceItem(
                    pmid=chunk.pmid,
                    title=title,
                    journal=journal,
                    publication_date=pub_date,
                    doi=doi,
                    authors=authors if isinstance(authors, list) else [],
                    disease_name=disease_name,
                    target_symbol=target_symbol,
                    evidence_text=context,
                    evidence_type=evidence_type,
                    relation=relation,
                    evidence_strength=evidence_strength,
                    direction=direction,
                    confidence=confidence,
                    source="PubMed"
                )
            )

        evidence_items = self._deduplicate_evidence(
            evidence_items
        )

        return EvidenceExtractionResult(
            target_symbol=target_symbol,
            disease_name=disease_name,
            evidence_items=evidence_items
        )

    def _build_context(
        self,
        sentences: list[str],
        target_index: int
    ) -> str:

        start = max(
            0,
            target_index - self.context_sentences
        )

        end = min(
            len(sentences),
            target_index + self.context_sentences + 1
        )

        return " ".join(
            sentence.strip()
            for sentence in sentences[start:end]
            if sentence.strip()
        )

    @staticmethod
    def _split_sentences(
        text: str
    ) -> list[str]:

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text
        )

        return [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

    @staticmethod
    def _calculate_confidence(
        context: str,
        target_symbol: str,
        disease_name: str,
        evidence_type: str,
        relation: str,
        direction: str,
        synonyms: list[str] | None = None
    ) -> float:

        score = 0.0

        # Target explicitly appears.
        if contains_target(
            context,
            target_symbol
        ):
            score += 0.25

        # Disease explicitly appears.
        if contains_disease(
            context,
            disease_name,
            synonyms=synonyms
        ):
            score += 0.25

        # Evidence type is recognizable.
        if evidence_type != "unknown":
            score += 0.20

        # Relationship has been identified.
        if relation != "mentions":
            score += 0.20

        # Direction is explicitly supported.
        if direction != "unknown":
            score += 0.10

        return min(
            score,
            1.0
        )

    @staticmethod
    def _deduplicate_evidence(
        evidence_items: list[EvidenceItem]
    ) -> list[EvidenceItem]:

        unique = {}

        for item in evidence_items:

            key = (
                item.pmid,
                item.target_symbol,
                item.evidence_text
            )

            if key not in unique:
                unique[key] = item

        return list(unique.values())