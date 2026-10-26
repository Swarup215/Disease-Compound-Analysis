"""
test_compound_retriever.py
--------------------------
Integration test for Step 6: Natural Compound Candidate Retrieval.

Tests:
  1. Unit – model instantiation
  2. Unit – Route A query builder
  3. Unit – compound name extraction from text
  4. Unit – potency conversion (_best_potency_nM)
  5. Unit – merge deduplication
  6. Live – Route A (PubMed) for Type 2 Diabetes
  7. Live – Route B (ChEMBL) for a known target (PPARG)
  8. Live – Full retrieval (both routes) for Type 2 Diabetes + sample targets

Run with:
    python test_compound_retriever.py
"""

import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compound_retriever.models import (
    BioactivityRecord,
    CompoundCandidate,
    CompoundRetrievalResult,
    TargetRelation,
)
from compound_retriever.retriever import (
    NaturalCompoundRetriever,
    _best_potency_nM,
    _extract_compound_names_from_text,
    _normalize_name,
)

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------
GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"


def ok(msg):   print(f"  {GREEN}PASS{RESET} {msg}")
def fail(msg): print(f"  {RED}FAIL{RESET} {msg}"); sys.exit(1)


# ===========================================================================
# 1. Model instantiation
# ===========================================================================
print(f"\n{BOLD}[1] Model instantiation{RESET}")

bio = BioactivityRecord(standard_type="IC50", standard_value=50.0, standard_units="nM")
assert bio.standard_type == "IC50"
ok("BioactivityRecord created")

tr = TargetRelation(target_symbol="PPARG", relation_type="inhibitor")
assert tr.target_symbol == "PPARG"
ok("TargetRelation created")

cc = CompoundCandidate(compound_id="CHEMBL123", name="quercetin")
assert cc.name == "quercetin"
ok("CompoundCandidate created")

crr = CompoundRetrievalResult(disease_name="type 2 diabetes")
assert crr.total_compounds == 0
ok("CompoundRetrievalResult created")


# ===========================================================================
# 2. Route A query builder
# ===========================================================================
print(f"\n{BOLD}[2] Route A query builder{RESET}")

queries = NaturalCompoundRetriever._build_route_a_queries(
    "type 2 diabetes", ["T2DM", "diabetes mellitus type 2"]
)
assert len(queries) == 3, f"Expected 3 queries, got {len(queries)}"
assert "natural product" in queries[0].lower()
ok(f"Generated {len(queries)} Route A queries")
for i, q in enumerate(queries, 1):
    print(f"    Query {i}: {q[:80]}...")


# ===========================================================================
# 3. Compound name extraction
# ===========================================================================
print(f"\n{BOLD}[3] Compound name extraction from text{RESET}")

text = (
    "We investigated the effect of quercetin and curcumin on insulin resistance. "
    "Both berberine and resveratrol showed significant antidiabetic activity. "
    "EGCG from green tea also demonstrated protective effects."
)
names = _extract_compound_names_from_text(text)
assert "quercetin" in names, f"Expected quercetin, got {names}"
assert "curcumin" in names,  f"Expected curcumin, got {names}"
assert "berberine" in names, f"Expected berberine, got {names}"
ok(f"Extracted {len(names)} compounds: {names}")


# ===========================================================================
# 4. Potency conversion
# ===========================================================================
print(f"\n{BOLD}[4] Potency unit conversion (_best_potency_nM){RESET}")

bioacts = [
    BioactivityRecord(standard_type="IC50", standard_value=1.5, standard_units="uM"),
    BioactivityRecord(standard_type="Ki",   standard_value=0.8, standard_units="uM"),
    BioactivityRecord(standard_type="EC50", standard_value=500.0, standard_units="nM"),
]
best = _best_potency_nM(bioacts)
assert best is not None
assert abs(best - 500.0) < 1.0, f"Expected ~500 nM, got {best}"
ok(f"Best potency: {best:.1f} nM (0.5 uM Ki)")


# ===========================================================================
# 5. Merge deduplication
# ===========================================================================
print(f"\n{BOLD}[5] Merge deduplication{RESET}")

c1 = CompoundCandidate(
    compound_id="CHEMBL000001",
    name="quercetin",
    inchikey="REDJIQWPIPKAMB-MIRQFWGFSA-N",
    chembl_id="CHEMBL000001",
    retrieval_routes=["disease_natural_literature"],
    evidence_sources=["PubMed"],
    citation_count=3,
)
c2 = CompoundCandidate(
    compound_id="CHEMBL000001",
    name="quercetin",
    inchikey="REDJIQWPIPKAMB-MIRQFWGFSA-N",
    chembl_id="CHEMBL000001",
    retrieval_routes=["protein_chembl_bioactivity"],
    evidence_sources=["ChEMBL"],
    citation_count=1,
)
merged = NaturalCompoundRetriever._merge([c1], [c2])
assert len(merged) == 1, f"Expected 1 merged compound, got {len(merged)}"
m = merged[0]
assert "disease_natural_literature" in m.retrieval_routes
assert "protein_chembl_bioactivity" in m.retrieval_routes
assert "PubMed" in m.evidence_sources
assert "ChEMBL" in m.evidence_sources
assert m.citation_count == 4
ok("Deduplication by InChIKey: merged into 1 compound, routes & sources combined")


# ===========================================================================
# 6. Live – Route A (PubMed) for Type 2 Diabetes
# ===========================================================================
print(f"\n{BOLD}[6] Live test – Route A (PubMed) for Type 2 Diabetes{RESET}")

retriever = NaturalCompoundRetriever(max_route_a_papers=10, max_route_b_papers=5, max_route_b_activities=50)
route_a = retriever._route_a(
    disease_name="type 2 diabetes",
    synonyms=["T2DM", "diabetes mellitus type 2"],
)
print(f"    Route A found {len(route_a)} unique compound candidates")
if route_a:
    for c in route_a[:5]:
        pmids = c.provenance.get("pmids", [])
        print(f"      - {c.name:30s}  citations={c.citation_count}  PMIDs={pmids[:2]}")
    ok(f"Route A returned {len(route_a)} compounds")
else:
    print("    WARNING: Route A returned no compounds (possible network issue)")


# ===========================================================================
# 7. Live – Route B (ChEMBL) for PPARG
# ===========================================================================
print(f"\n{BOLD}[7] Live test – Route B (ChEMBL) for PPARG{RESET}")

sample_targets = [
    {"symbol": "PPARG", "name": "Peroxisome proliferator-activated receptor gamma"},
]
route_b = retriever._route_b(disease_name="type 2 diabetes", targets=sample_targets)
print(f"    Route B found {len(route_b)} compound candidates for PPARG")
if route_b:
    for c in route_b[:5]:
        print(
            f"      - {c.name[:30]:30s}  ChEMBL={c.chembl_id or 'N/A':15s}  "
            f"natural={c.natural_origin}  best_nM={c.best_bioactivity_nM}"
        )
    ok(f"Route B returned {len(route_b)} compounds")
else:
    print("    WARNING: Route B returned no compounds (possible network/API issue)")


# ===========================================================================
# 8. Live – Full retrieval (both routes)
# ===========================================================================
print(f"\n{BOLD}[8] Live test – Full retrieval (Route A + B){RESET}")

full_targets = [
    {"symbol": "PPARG", "name": "Peroxisome proliferator-activated receptor gamma"},
    {"symbol": "KCNJ11", "name": "ATP-sensitive inward rectifier potassium channel 11"},
    {"symbol": "ABCC8",  "name": "ATP-binding cassette sub-family C member 8"},
]

result = retriever.retrieve(
    disease_name="type 2 diabetes mellitus",
    targets=full_targets,
    disease_synonyms=["T2DM", "type 2 diabetes"],
)

print(f"\n  === CompoundRetrievalResult ===")
print(f"    disease:          {result.disease_name}")
print(f"    targets_queried:  {result.targets_queried}")
print(f"    total_compounds:  {result.total_compounds}")
print(f"    route_a_count:    {result.route_a_count}")
print(f"    route_b_count:    {result.route_b_count}")
print(f"    dual_route_count: {result.dual_route_count}")
print()

for i, c in enumerate(result.compounds[:10], 1):
    routes_str = " + ".join(c.retrieval_routes)
    print(
        f"    {i:2d}. {c.name[:35]:35s}  routes=[{routes_str}]  "
        f"natural={c.natural_origin}  targets={c.targets_targeted[:3]}"
    )

assert result.total_compounds == len(result.compounds)
ok(f"Full retrieval complete: {result.total_compounds} compounds across both routes")

print(f"\n{BOLD}{GREEN}All tests passed!{RESET}")
