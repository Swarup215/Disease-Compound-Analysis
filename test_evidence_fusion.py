from evidence_fusion import (
    TargetFusionInput,
    EvidenceFusion
)


fusion = EvidenceFusion()


kcnj11 = TargetFusionInput(
    target_id="ENSG00000187486",
    target_symbol="KCNJ11",
    structured_score=0.8772,
    evidence_count=2,
    strong_evidence_count=1,
    moderate_evidence_count=1,
    weak_evidence_count=0
)


result = fusion.fuse(kcnj11)


print("=" * 80)
print("EVIDENCE FUSION TEST")
print("=" * 80)

print(f"Target: {result.target_symbol}")
print(f"Structured score: {result.structured_score}")
print(f"Evidence count: {result.evidence_count}")
print(f"Strong evidence: {result.strong_evidence_count}")
print(f"Moderate evidence: {result.moderate_evidence_count}")
print(f"Weak evidence: {result.weak_evidence_count}")
print(f"Literature score: {result.literature_score}")
print(f"Fused score: {result.fused_score}")

print("=" * 80)
print("EVIDENCE FUSION TEST COMPLETED")
print("=" * 80)