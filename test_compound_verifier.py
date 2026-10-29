"""
test_compound_verifier.py
-------------------------
Comprehensive test suite for Step 7: Compound Identity & Natural-Origin Verification.

Tests:
  1. Unit – Model instantiation and validation
  2. Unit – InChIKey syntax validation
  3. Unit – Natural vs. Synthetic classification (curated registry & heuristics)
  4. Unit – Provenance retention and audit trail
  5. Live – PubChem API resolution by name (Quercetin -> CID 5280343)
  6. Live – PubChem API resolution by InChIKey (Resveratrol)
  7. Live – Batch verification & sorting on mixed natural/synthetic candidates

Run with:
    python test_compound_verifier.py
"""

import sys
import os

# Allow running from project root or inside Disease-Compound-Analysis
cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

from compound_verifier.models import (
    CompoundIdentity,
    CompoundVerificationBatchResult,
    NaturalOriginStatus,
    NaturalOriginVerification,
    VerifiedCompound,
)
from compound_verifier.pubchem_client import PubChemClient
from compound_verifier.natural_classifier import NaturalOriginClassifier
from compound_verifier.verifier import CompoundVerifier

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
# 1. Model Instantiation
# ===========================================================================
print(f"\n{BOLD}[1] Model instantiation and validation{RESET}")

ident = CompoundIdentity(
    name="quercetin",
    iupac_name="2-(3,4-dihydroxyphenyl)-3,5,7-trihydroxychromen-4-one",
    pubchem_cid=5280343,
    inchikey="REFJWTPEDVJJIY-UHFFFAOYSA-N",
    canonical_smiles="C1=CC(=C(C=C1C2=C(C(=O)C3=C(C=C(C=C3O2)O)O)O)O)O",
    molecular_formula="C15H10O7",
    molecular_weight=302.23,
    synonyms=["Sophoretin", "Meletin"],
)
assert ident.pubchem_cid == 5280343
assert ident.inchikey == "REFJWTPEDVJJIY-UHFFFAOYSA-N"
ok("CompoundIdentity instantiated successfully")

verif = NaturalOriginVerification(
    status=NaturalOriginStatus.NATURAL,
    is_natural=True,
    confidence=0.98,
    natural_product_class="Flavonoid",
    subclass="Flavonol",
    determination_method="curated_phytochemical_registry",
    evidence_sources=["Curated_Natural_Registry", "PubChem"],
)
assert verif.is_natural is True
assert verif.status == NaturalOriginStatus.NATURAL
ok("NaturalOriginVerification instantiated successfully")

vc = VerifiedCompound(
    compound_id="CID:5280343",
    name="quercetin",
    identity=ident,
    natural_verification=verif,
    retrieval_routes=["disease_natural_literature", "protein_literature"],
    targets_targeted=["PPARG", "KCNJ11"],
    citation_count=5,
    is_dual_route=True,
    provenance={"pmids": ["12345678"], "snippets": ["Quercetin inhibits PPARG."]},
)
assert vc.is_dual_route is True
assert "PPARG" in vc.targets_targeted
ok("VerifiedCompound instantiated successfully")

batch = CompoundVerificationBatchResult(
    disease_name="Type 2 Diabetes",
    total_candidates=1,
    verified_natural_count=1,
    compounds=[vc],
)
assert batch.verified_natural_count == 1
ok("CompoundVerificationBatchResult instantiated successfully")


# ===========================================================================
# 2. InChIKey Syntax Validation
# ===========================================================================
print(f"\n{BOLD}[2] InChIKey syntax validation{RESET}")

valid_key = "REFJWTPEDVJJIY-UHFFFAOYSA-N"
invalid_key_1 = "REFJWTPEDVJJIY"
invalid_key_2 = "refjwtpedvjjiy-uhffpaoysa-n"  # lowercase
invalid_key_3 = "REFJWTPEDVJJIY-UHFFFAOYSA-12"

assert PubChemClient.is_valid_inchikey(valid_key) is True
assert PubChemClient.is_valid_inchikey(invalid_key_1) is False
assert PubChemClient.is_valid_inchikey(invalid_key_2) is False
assert PubChemClient.is_valid_inchikey(invalid_key_3) is False
assert PubChemClient.is_valid_inchikey(None) is False
ok("InChIKey format validation passed (14-10-1 format)")


# ===========================================================================
# 3. Natural vs. Synthetic Classification
# ===========================================================================
print(f"\n{BOLD}[3] Natural vs. Synthetic origin classification{RESET}")

classifier = NaturalOriginClassifier()

# 3.1 Known natural products
q_res = classifier.classify("quercetin")
assert q_res.status == NaturalOriginStatus.NATURAL
assert q_res.is_natural is True
assert q_res.natural_product_class == "Flavonoid"
assert q_res.subclass == "Flavonol"
ok(f"Quercetin classified as {q_res.status.value} ({q_res.natural_product_class} / {q_res.subclass})")

b_res = classifier.classify("berberine")
assert b_res.status == NaturalOriginStatus.NATURAL
assert b_res.natural_product_class == "Alkaloid"
ok(f"Berberine classified as {b_res.status.value} ({b_res.natural_product_class})")

c_res = classifier.classify("curcumin")
assert c_res.status == NaturalOriginStatus.NATURAL
assert c_res.natural_product_class == "Polyphenol"
ok(f"Curcumin classified as {c_res.status.value} ({c_res.natural_product_class})")

# 3.2 Known synthetic drugs
met_res = classifier.classify("metformin")
assert met_res.status == NaturalOriginStatus.SYNTHETIC
assert met_res.is_natural is False
assert met_res.subclass == "Biguanide"
ok(f"Metformin classified as {met_res.status.value} ({met_res.subclass})")

rosi_res = classifier.classify("rosiglitazone")
assert rosi_res.status == NaturalOriginStatus.SYNTHETIC
assert rosi_res.is_natural is False
assert rosi_res.subclass == "Thiazolidinedione"
ok(f"Rosiglitazone classified as {rosi_res.status.value} ({rosi_res.subclass})")

# 3.3 Semi-synthetic natural derivative
asp_res = classifier.classify("aspirin")
assert asp_res.status == NaturalOriginStatus.NATURAL_DERIVATIVE
assert asp_res.is_natural is True
ok(f"Aspirin classified as {asp_res.status.value} (Semi-synthetic natural derivative)")

# 3.4 Unverified
unk_res = classifier.classify("xyz-synthetic-compound-999")
assert unk_res.status == NaturalOriginStatus.UNVERIFIED
assert unk_res.is_natural is False
ok(f"Unknown chemical correctly classified as {unk_res.status.value}")


# ===========================================================================
# 4. Provenance Retention
# ===========================================================================
print(f"\n{BOLD}[4] Provenance retention and audit trail{RESET}")

verifier = CompoundVerifier(enable_pubchem=False)  # test local pipeline logic
sample_candidate = {
    "compound_id": "LIT:BERBERINE",
    "name": "berberine",
    "retrieval_routes": ["disease_natural_literature", "protein_chembl_bioactivity"],
    "targets_targeted": ["PPARG"],
    "citation_count": 4,
    "best_bioactivity_nM": 350.0,
    "provenance": {
        "pmids": ["31234567", "32345678"],
        "snippets": ["Berberine improves insulin sensitivity."],
    },
}

verified_item = verifier.verify_compound(sample_candidate)
assert "pmids" in verified_item.provenance
assert "snippets" in verified_item.provenance
assert "verification" in verified_item.provenance
assert verified_item.provenance["verification"]["origin_status"] == "natural"
assert verified_item.is_dual_route is True
assert verified_item.best_bioactivity_nM == 350.0
ok("Original Step 6 PMIDs, snippets, potencies, and dual-route flags preserved in provenance")


# ===========================================================================
# 5. Live PubChem API Resolution by Name
# ===========================================================================
print(f"\n{BOLD}[5] Live test – PubChem API resolution for Quercetin{RESET}")

pubchem = PubChemClient()
q_ident = pubchem.resolve_identity(name="quercetin", fetch_synonyms=True)

if q_ident:
    assert q_ident["pubchem_cid"] == 5280343, f"Expected CID 5280343, got {q_ident.get('pubchem_cid')}"
    assert "REFJWTPEDVJJIY" in (q_ident.get("inchikey") or ""), f"Unexpected InChIKey: {q_ident.get('inchikey')}"
    assert "C15H10O7" == q_ident.get("molecular_formula")
    assert len(q_ident.get("synonyms", [])) > 0
    ok(f"Quercetin resolved: CID={q_ident['pubchem_cid']}, InChIKey={q_ident['inchikey']}, MW={q_ident['molecular_weight']}")
    print(f"    Synonyms sample: {q_ident['synonyms'][:4]}")
else:
    print("    WARNING: PubChem API query returned None (possible network issue)")


# ===========================================================================
# 6. Live PubChem API Resolution by InChIKey
# ===========================================================================
print(f"\n{BOLD}[6] Live test – PubChem API resolution by InChIKey (Resveratrol){RESET}")

resv_inchikey = "LUKBXSAWLPMMSZ-OWOJBTEDSA-N"
resv_ident = pubchem.resolve_identity(inchikey=resv_inchikey, fetch_synonyms=False)

if resv_ident:
    assert resv_ident["pubchem_cid"] == 445154, f"Expected CID 445154, got {resv_ident.get('pubchem_cid')}"
    assert "C14H12O3" == resv_ident.get("molecular_formula")
    ok(f"Resveratrol resolved by InChIKey: CID={resv_ident['pubchem_cid']}, Formula={resv_ident['molecular_formula']}")
else:
    print("    WARNING: PubChem API query returned None (possible network issue)")


# ===========================================================================
# 7. Live Batch Verification & Sorting
# ===========================================================================
print(f"\n{BOLD}[7] Live test – Batch verification on mixed candidate pool{RESET}")

live_verifier = CompoundVerifier(enable_pubchem=True)

test_candidates = [
    {
        "name": "metformin",
        "retrieval_routes": ["protein_chembl_bioactivity"],
        "targets_targeted": ["PRKAA1"],
        "citation_count": 10,
    },
    {
        "name": "quercetin",
        "retrieval_routes": ["disease_natural_literature", "protein_literature"],
        "targets_targeted": ["PPARG", "ABCC8"],
        "citation_count": 8,
        "best_bioactivity_nM": 120.0,
    },
    {
        "name": "aspirin",
        "retrieval_routes": ["disease_natural_literature"],
        "targets_targeted": ["PTGS1"],
        "citation_count": 15,
    },
    {
        "name": "curcumin",
        "retrieval_routes": ["protein_literature"],
        "targets_targeted": ["PPARG"],
        "citation_count": 12,
    },
]

batch_result = live_verifier.verify_batch(test_candidates, disease_name="Type 2 diabetes")

print(f"\n  === CompoundVerificationBatchResult ===")
print(f"    Total candidates:        {batch_result.total_candidates}")
print(f"    Verified Natural:        {batch_result.verified_natural_count}")
print(f"    Natural Derivatives:     {batch_result.natural_derivative_count}")
print(f"    Synthetic Compounds:     {batch_result.synthetic_count}")
print(f"    Unverified Compounds:    {batch_result.unverified_count}")
print()

for i, c in enumerate(batch_result.compounds, 1):
    status_str = c.natural_verification.status.value.upper()
    cid_str = f"CID:{c.identity.pubchem_cid}" if c.identity.pubchem_cid else "CID:N/A"
    formula_str = c.identity.molecular_formula or "N/A"
    print(
        f"    {i}. {c.name.capitalize():15s} | Status: {status_str:18s} | {cid_str:12s} | "
        f"Class: {c.natural_verification.natural_product_class or 'N/A':20s} | "
        f"Formula: {formula_str}"
    )

# Validate ordering: Natural & Natural Derivatives must precede Synthetic
first_status = batch_result.compounds[0].natural_verification.status
last_status = batch_result.compounds[-1].natural_verification.status
assert first_status in (NaturalOriginStatus.NATURAL, NaturalOriginStatus.NATURAL_DERIVATIVE)
assert last_status == NaturalOriginStatus.SYNTHETIC
ok("Batch sorting correctly places verified natural products first and separates synthetic drugs")

print(f"\n{BOLD}{GREEN}All Step 7 tests passed successfully!{RESET}")

