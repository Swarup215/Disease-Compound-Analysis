"""
models.py
---------
Step 7: Compound Identity & Natural-Origin Verification Data Models.

Defines Pydantic models for chemical identity resolution (PubChem CID,
canonical SMILES, InChIKey, IUPAC name, synonyms), natural vs. synthetic
origin classification, confidence scoring, and full audit provenance.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Import TargetRelation from compound_retriever for provenance retention
try:
    from compound_retriever.models import TargetRelation
except ImportError:
    TargetRelation = Any  # type: ignore


class NaturalOriginStatus(str, Enum):
    """Categorical classification of compound origin."""
    NATURAL = "natural"                       # Directly isolated from botanical/microbial/marine source
    NATURAL_DERIVATIVE = "natural_derivative" # Semi-synthetic derivative of a natural scaffold
    SYNTHETIC = "synthetic"                   # Entirely man-made / synthetic medicinal chemistry entity
    UNVERIFIED = "unverified"                 # Insufficient evidence to conclusively classify


class CompoundIdentity(BaseModel):
    """Standardized chemical identity descriptors from authoritative chemical registries."""
    name: str = Field(..., description="Standardized common or preferred compound name")
    iupac_name: Optional[str] = Field(None, description="Systematic IUPAC name")
    pubchem_cid: Optional[int] = Field(None, description="PubChem Compound ID (CID)")
    inchikey: Optional[str] = Field(None, description="Standard InChIKey (14-10-1 format, 27 chars)")
    canonical_smiles: Optional[str] = Field(None, description="Canonical SMILES representation")
    isomeric_smiles: Optional[str] = Field(None, description="Stereospecific isomeric SMILES representation")
    molecular_formula: Optional[str] = Field(None, description="Hill-system molecular formula (e.g. C15H10O7)")
    molecular_weight: Optional[float] = Field(None, description="Average molecular weight in g/mol")
    synonyms: List[str] = Field(default_factory=list, description="Authoritative chemical synonyms and trade names")


class NaturalOriginVerification(BaseModel):
    """Verification assessment distinguishing natural vs. synthetic origins."""
    status: NaturalOriginStatus = Field(
        NaturalOriginStatus.UNVERIFIED,
        description="Categorical origin classification"
    )
    is_natural: bool = Field(
        False,
        description="Boolean summary: True if natural or natural_derivative, False otherwise"
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score [0.0 - 1.0] in the origin assignment"
    )
    natural_product_class: Optional[str] = Field(
        None,
        description="Phytochemical superclass: Flavonoid, Polyphenol, Alkaloid, Terpenoid, etc."
    )
    subclass: Optional[str] = Field(
        None,
        description="Phytochemical subclass: Flavonol, Isoflavone, Stilbene, Triterpenoid, etc."
    )
    determination_method: str = Field(
        "unverified",
        description="Method used for classification (e.g., 'pubchem_xref_plus_curated', 'phytochemical_taxonomy')"
    )
    evidence_sources: List[str] = Field(
        default_factory=list,
        description="Databases/resources validating this assignment (PubChem, ChEMBL, Curated, etc.)"
    )
    notes: Optional[str] = Field(
        None,
        description="Explanatory clinical or botanical notes on the compound classification"
    )


class VerifiedCompound(BaseModel):
    """
    Fully verified compound candidate with resolved chemical identity,
    substantiated natural-origin classification, and preserved Step 6 provenance.
    """
    compound_id: str = Field(..., description="Unique persistent identifier (CID:xxx or CHEMBLxxx)")
    name: str = Field(..., description="Standardized common compound name")
    identity: CompoundIdentity = Field(..., description="Standardized chemical identity")
    natural_verification: NaturalOriginVerification = Field(
        ...,
        description="Natural vs. synthetic verification details"
    )
    retrieval_routes: List[str] = Field(
        default_factory=list,
        description="Preserved Step 6 routes: 'disease_natural_literature', 'protein_chembl_bioactivity', etc."
    )
    targets_targeted: List[str] = Field(
        default_factory=list,
        description="Target protein symbols this compound is active against or mentioned with"
    )
    target_relations: List[Any] = Field(
        default_factory=list,
        description="Detailed TargetRelation records with bioactivities, potencies, and citations"
    )
    evidence_sources: List[str] = Field(
        default_factory=list,
        description="Origin data sources: PubChem, ChEMBL, PubMed, Europe PMC, etc."
    )
    citation_count: int = Field(0, description="Total publications mentioning this compound")
    best_bioactivity_nM: Optional[float] = Field(
        None,
        description="Best (lowest) potency IC50/Ki/Kd in nM across all target relations"
    )
    is_dual_route: bool = Field(
        False,
        description="True if retrieved via both Route A (disease literature) and Route B (protein bioactivity)"
    )
    provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Complete audit trail: query history, PMIDs, snippets, API timestamps, and validation metrics"
    )


class CompoundVerificationBatchResult(BaseModel):
    """Aggregated output of Step 7 Compound Identity & Natural-Origin Verification."""
    disease_name: Optional[str] = Field(None, description="Associated disease name (if pipeline run)")
    total_candidates: int = Field(0, description="Total candidates evaluated")
    verified_natural_count: int = Field(0, description="Compounds verified as natural products")
    natural_derivative_count: int = Field(0, description="Compounds identified as semi-synthetic derivatives")
    synthetic_count: int = Field(0, description="Compounds classified as synthetic entities")
    unverified_count: int = Field(0, description="Compounds with indeterminate origin")
    compounds: List[VerifiedCompound] = Field(
        default_factory=list,
        description="Prioritized list of verified compound records"
    )

