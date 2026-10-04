from evidence_fusion.models import TargetFusionResult
from target_prioritization.prioritizer import TargetPrioritizer


fusion_results = [
    TargetFusionResult(
        target_id="ENSG00000187486",
        target_symbol="KCNJ11",
        structured_score=0.8772,
        evidence_count=1,
        strong_evidence_count=1,
        moderate_evidence_count=0,
        weak_evidence_count=0,
        literature_score=1.0,
        literature_status="evidence_found",
        fused_score=0.9263
    ),
    TargetFusionResult(
        target_id="ENSG00000006071",
        target_symbol="ABCC8",
        structured_score=0.8764,
        evidence_count=0,
        literature_score=0.0,
        literature_status="no_evidence",
        fused_score=0.5258
    ),
    TargetFusionResult(
        target_id="ENSG00000106633",
        target_symbol="GCK",
        structured_score=0.8680,
        evidence_count=0,
        literature_score=0.0,
        literature_status="no_evidence",
        fused_score=0.5208
    )
]

prioritizer = TargetPrioritizer()

result = prioritizer.prioritize(
    fusion_results=fusion_results,
    top_n=3
)

print("=" * 80)
print("TARGET PRIORITIZATION TEST")
print("=" * 80)

print(f"Total targets: {result.total_targets}")
print(f"Selected targets: {result.selected_targets}")

for target in result.targets:

    print(
        f"{target.rank}. {target.target_symbol}"
    )

    print(
        f"   Fused score: {target.fused_score:.4f}"
    )

    print(
        f"   Literature status: "
        f"{target.literature_status}"
    )

    print(
        f"   Evidence count: "
        f"{target.evidence_count}"
    )

    print("-" * 80)

print("TARGET PRIORITIZATION TEST COMPLETED")
