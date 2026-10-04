from evidence_extractor.models import EvidenceItem

from evidence_graph.models import (
    DiseaseNode,
    TargetNode,
    PaperNode,
    EvidenceNode,
    EvidenceEdge,
    EvidenceGraph
)


class EvidenceGraphBuilder:

    def __init__(self):
        self.graph = EvidenceGraph()

    def add_disease(
        self,
        disease_id: str,
        disease_name: str
    ):

        existing = next(
            (
                disease
                for disease in self.graph.diseases
                if disease.id == disease_id
            ),
            None
        )

        if existing is None:

            self.graph.diseases.append(
                DiseaseNode(
                    id=disease_id,
                    name=disease_name
                )
            )

    def add_target(
        self,
        target_id: str,
        symbol: str,
        name: str | None = None
    ):

        existing = next(
            (
                target
                for target in self.graph.targets
                if target.id == target_id
            ),
            None
        )

        if existing is None:

            self.graph.targets.append(
                TargetNode(
                    id=target_id,
                    symbol=symbol,
                    name=name
                )
            )

    def add_paper(
        self,
        pmid: str,
        title: str | None = None
    ):

        existing = next(
            (
                paper
                for paper in self.graph.papers
                if paper.pmid == pmid
            ),
            None
        )

        if existing is None:

            self.graph.papers.append(
                PaperNode(
                    pmid=pmid,
                    title=title
                )
            )

    def add_edge(
        self,
        source_id: str,
        relation: str,
        target_id: str
    ):

        edge = EvidenceEdge(
            source_id=source_id,
            relation=relation,
            target_id=target_id
        )

        # Prevent duplicate edges.
        if edge not in self.graph.edges:
            self.graph.edges.append(edge)

    def add_evidence(
        self,
        evidence: EvidenceItem
    ):

        evidence_id = (
            f"EVIDENCE:"
            f"{evidence.pmid}:"
            f"{evidence.target_symbol}:"
            f"{len(self.graph.evidence)}"
        )

        evidence_node = EvidenceNode(
            id=evidence_id,
            pmid=evidence.pmid,
            disease_name=evidence.disease_name,
            target_symbol=evidence.target_symbol,
            evidence_text=evidence.evidence_text,
            evidence_type=evidence.evidence_type,
            relation=evidence.relation,
            evidence_strength=evidence.evidence_strength,
            direction=evidence.direction,
            confidence=evidence.confidence
        )

        self.graph.evidence.append(
            evidence_node
        )

        # -----------------------------------------------------
        # Connect target -> evidence
        # -----------------------------------------------------

        target = next(
            (
                target
                for target in self.graph.targets
                if target.symbol == evidence.target_symbol
            ),
            None
        )

        if target is not None:

            self.add_edge(
                source_id=target.id,
                relation="supported_by",
                target_id=evidence_id
            )

        # -----------------------------------------------------
        # Connect evidence -> paper
        # -----------------------------------------------------

        if evidence.pmid:

            paper_id = f"PMID:{evidence.pmid}"

            self.add_edge(
                source_id=evidence_id,
                relation="reported_in",
                target_id=paper_id
            )

        # -----------------------------------------------------
        # Connect disease -> target
        # -----------------------------------------------------

        disease = next(
            (
                disease
                for disease in self.graph.diseases
                if disease.name.lower()
                == evidence.disease_name.lower()
            ),
            None
        )

        if disease is not None and target is not None:

            self.add_edge(
                source_id=disease.id,
                relation=evidence.relation,
                target_id=target.id
            )

    def add_extraction_result(
        self,
        evidence_items: list[EvidenceItem]
    ):

        for evidence in evidence_items:
            self.add_evidence(evidence)

    def build(self) -> EvidenceGraph:

        return self.graph