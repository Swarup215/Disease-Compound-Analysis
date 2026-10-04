from evidence_fusion import EvidenceFusion
from evidence_graph import EvidenceGraph, EvidenceNode


graph = EvidenceGraph()

# Simulate evidence already extracted by the real Evidence Extractor.
graph.evidence = [
    EvidenceNode(
        id="EVIDENCE:1",
        pmid="41947234",
        disease_name="type 2 diabetes mellitus",
        target_symbol="KCNJ11",
        evidence_text="Example genetic evidence",
        evidence_type="genetic_association",
        relation="associated_with",
        evidence_strength="strong",
        direction="unknown",
        confidence=0.9
    ),

    EvidenceNode(
        id="EVIDENCE:2",
        pmid="42227366",
        disease_name="type 2 diabetes mellitus",
        target_symbol="KCNJ11",
        evidence_text="Example drug target evidence",
        evidence_type="drug_target",
        relation="drug_target_of",
        evidence_strength="moderate",
        direction="unknown",
        confidence=0.9
    ),

    EvidenceNode(
        id="EVIDENCE:3",
        pmid="42227366",
        disease_name="type 2 diabetes mellitus",
        target_symbol="ABCC8",
        evidence_text="Example drug target evidence",
        evidence_type="drug_target",
        relation="drug_target_of",
        evidence_strength="moderate",
        direction="unknown",
        confidence=0.9
    )
]


fusion = EvidenceFusion()


targets = [
    ("ENSG00000187486", "KCNJ11", 0.8772),
    ("ENSG00000006071", "ABCC8", 0.8764),
    ("ENSG00000106633", "GCK", 0.8680),
]


for target_id, target_symbol, structured_score in targets:

    target_input = fusion.build_target_input(
        target_id=target_id,
        target_symbol=target_symbol,
        structured_score=structured_score,
        evidence_graph=graph
    )

    result = fusion.fuse(target_input)

    print("=" * 60)
    print(f"Target: {result.target_symbol}")
    print(f"Structured score: {result.structured_score}")
    print(f"Evidence count: {result.evidence_count}")
    print(f"Strong evidence: {result.strong_evidence_count}")
    print(f"Moderate evidence: {result.moderate_evidence_count}")
    print(f"Weak evidence: {result.weak_evidence_count}")
    print(f"Literature score: {result.literature_score}")
    print(f"Fused score: {result.fused_score}")