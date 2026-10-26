from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BioactivityRecord(BaseModel):
    """Represents a quantitative or qualitative bioactivity measurement (e.g. from ChEMBL)."""
    activity_id: Optional[str] = Field(None, description="ChEMBL activity ID or assay record ID")
    standard_type: str = Field(..., description="Bioactivity assay type: IC50, Ki, Kd, EC50, Inhibition, etc.")
    standard_value: Optional[float] = Field(None, description="Numeric bioactivity value")
    standard_units: Optional[str] = Field(None, description="Units of measurement (e.g., nM, uM, %)")
    standard_relation: Optional[str] = Field("=", description="Relation symbol (=, <, >, <=, >=)")
    assay_type: Optional[str] = Field(None, description="Assay format code (B: binding, F: functional, A: ADMET)")
    assay_description: Optional[str] = Field(None, description="Textual description of the experimental assay")
    target_chembl_id: Optional[str] = Field(None, description="ChEMBL target identifier")
    target_symbol: Optional[str] = Field(None, description="Associated gene/protein symbol")
    document_chembl_id: Optional[str] = Field(None, description="Source publication ChEMBL document ID")
    pmid: Optional[str] = Field(None, description="PubMed ID of publication reporting this bioactivity")
    doi: Optional[str] = Field(None, description="DOI of publication")


class TargetRelation(BaseModel):
    """Direct compound-target relationship captured at retrieval time."""
    target_symbol: str = Field(..., description="Target gene/protein symbol (e.g. TNF, PPARG)")
    target_name: Optional[str] = Field(None, description="Target protein full name")
    uniprot_id: Optional[str] = Field(None, description="UniProt accession ID")
    target_chembl_id: Optional[str] = Field(None, description="Target ChEMBL ID")
    relation_type: str = Field(
        "active_against",
        description="Relationship type: inhibitor, antagonist, agonist, modulator, active_against, literature_mentioned"
    )
    bioactivities: List[BioactivityRecord] = Field(default_factory=list, description="Associated bioactivity measurements")
    best_potency_nM: Optional[float] = Field(None, description="Lowest IC50/Ki/Kd in nM for quick potency ranking")
    evidence_snippets: List[str] = Field(default_factory=list, description="Literature or assay text supporting this interaction")
    pmids: List[str] = Field(default_factory=list, description="PubMed IDs supporting this compound-target link")
    source: str = Field("ChEMBL", description="Source of relation: ChEMBL, PubMed, NaturalDB, etc.")


class CompoundCandidate(BaseModel):
    """Represents a discovered candidate natural or bioactive compound."""
    compound_id: str = Field(..., description="Unique compound identifier (e.g. CHEMBLxxx, PUBCHEM:xxx)")
    name: str = Field(..., description="Preferred or common compound name")
    synonyms: List[str] = Field(default_factory=list, description="Synonyms and alternative chemical names")
    smiles: Optional[str] = Field(None, description="Canonical SMILES structure string")
    inchikey: Optional[str] = Field(None, description="Standard InChIKey")
    pubchem_cid: Optional[int] = Field(None, description="PubChem Compound ID")
    chembl_id: Optional[str] = Field(None, description="ChEMBL Molecule ID")
    natural_origin: bool = Field(True, description="Whether verified or suspected to be of natural origin")
    natural_origin_source: Optional[str] = Field(None, description="Source certifying natural origin: COCONUT, Literature, Botanical, etc.")
    natural_product_class: Optional[str] = Field(None, description="Phytochemical/chemical class: Polyphenol, Flavonoid, Curcuminoid, etc.")
    retrieval_routes: List[str] = Field(
        default_factory=list,
        description="Retrieval routes: 'disease_natural_literature', 'protein_chembl_bioactivity', 'protein_literature'"
    )
    targets_targeted: List[str] = Field(default_factory=list, description="List of target symbols this compound targets")
    target_relations: List[TargetRelation] = Field(
        default_factory=list,
        description="Detailed compound-target relationships and evidence"
    )
    evidence_sources: List[str] = Field(default_factory=list, description="Origin sources: ChEMBL, PubMed, NaturalDB, etc.")
    citation_count: int = Field(0, description="Total publications mentioning this compound in target or disease context")
    best_bioactivity_nM: Optional[float] = Field(None, description="Best (lowest) IC50 / Ki across all linked targets")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Full audit trail of how this compound was retrieved")


class CompoundRetrievalResult(BaseModel):
    """Aggregated output of Step 6 Natural Compound Candidate Retrieval."""
    disease_name: str = Field(..., description="Query disease name")
    targets_queried: List[str] = Field(default_factory=list, description="Target protein symbols queried")
    total_compounds: int = Field(0, description="Total unique compounds retrieved")
    route_a_count: int = Field(0, description="Compounds retrieved via Route A (Disease -> Natural Compounds)")
    route_b_count: int = Field(0, description="Compounds retrieved via Route B (Protein -> Bioactive Compounds)")
    dual_route_count: int = Field(0, description="Compounds retrieved via BOTH Route A and Route B (highest prior confidence)")
    compounds: List[CompoundCandidate] = Field(default_factory=list, description="Prioritized list of candidate compounds")
