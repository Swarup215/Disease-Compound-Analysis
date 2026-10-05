import re
from typing import List, Optional, Set


def get_disease_search_terms(disease_name: str, synonyms: Optional[List[str]] = None) -> Set[str]:
    """
    Generate normalized variations, abbreviations, and synonyms for any disease.
    """
    if not disease_name or not disease_name.strip():
        return set()

    disease_clean = disease_name.strip().lower()
    terms: Set[str] = {disease_clean}

    # Clean punctuation and possessives (e.g. Alzheimer's -> Alzheimer)
    no_apostrophe = re.sub(r"['’]s\b", "", disease_clean)
    no_punct = re.sub(r"[^\w\s]", " ", disease_clean).strip()
    no_punct = re.sub(r"\s+", " ", no_punct)

    terms.add(no_apostrophe)
    terms.add(no_punct)

    # Remove generic disease noise words for partial match
    noise_words = ["disease", "syndrome", "disorder", "carcinoma", "cancer", "mellitus", "infection"]
    trimmed = no_punct
    for w in noise_words:
        trimmed = re.sub(rf"\b{w}\b", "", trimmed).strip()
    trimmed = re.sub(r"\s+", " ", trimmed).strip()
    if len(trimmed) >= 3:
        terms.add(trimmed)

    # Common disease-specific synonyms and acronyms
    alias_dict = {
        "type 2 diabetes": {"type 2 diabetes", "type 2 diabetes mellitus", "t2dm", "t2d", "diabetes mellitus", "non-insulin dependent diabetes", "niddm"},
        "type 1 diabetes": {"type 1 diabetes", "type 1 diabetes mellitus", "t1dm", "t1d", "juvenile diabetes"},
        "alzheimer": {"alzheimer", "alzheimer's", "alzheimers", "ad", "alzheimer disease", "alzheimer's disease"},
        "parkinson": {"parkinson", "parkinson's", "parkinsons", "pd", "parkinson disease"},
        "rheumatoid arthritis": {"rheumatoid arthritis", "ra", "rheumatoid"},
        "systemic lupus erythematosus": {"systemic lupus erythematosus", "sle", "lupus"},
        "breast cancer": {"breast cancer", "breast carcinoma", "breast neoplasm", "brca"},
        "asthma": {"asthma", "bronchial asthma", "allergic asthma"},
        "chronic kidney disease": {"chronic kidney disease", "ckd"},
        "multiple sclerosis": {"multiple sclerosis", "ms"},
        "amyotrophic lateral sclerosis": {"amyotrophic lateral sclerosis", "als"},
        "inflammatory bowel disease": {"inflammatory bowel disease", "ibd", "crohn's", "ulcerative colitis"},
        "hypertension": {"hypertension", "high blood pressure", "essential hypertension"},
    }

    for key, aliases in alias_dict.items():
        if key in disease_clean or any(k in disease_clean for k in key.split()):
            terms.update(aliases)

    # Add passed-in synonyms
    if synonyms:
        for syn in synonyms:
            if syn and syn.strip():
                s_clean = syn.strip().lower()
                terms.add(s_clean)
                terms.add(re.sub(r"['’]s\b", "", s_clean))

    return {t for t in terms if len(t) >= 2}


def contains_disease(text: str, disease_name: str, synonyms: Optional[List[str]] = None) -> bool:
    if not text or not disease_name:
        return False

    text_lower = text.lower()
    terms = get_disease_search_terms(disease_name, synonyms)

    # Check whole word boundaries or substring for multi-word terms
    for term in terms:
        if " " in term or len(term) >= 4:
            if term in text_lower:
                return True
        else:
            # Short acronyms require word boundary
            if re.search(rf"\b{re.escape(term)}\b", text_lower):
                return True

    return False


def contains_target(text: str, target_symbol: str) -> bool:
    if not text or not target_symbol:
        return False

    pattern = rf"\b{re.escape(target_symbol)}\b"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def classify_evidence_type(text: str) -> str:
    text_lower = text.lower()

    if any(phrase in text_lower for phrase in [
        "genetic association", "genetic variant", "genetic variants",
        "single-nucleotide polymorphism", "single nucleotide polymorphism",
        "snp", "locus", "loci", "allele", "polymorphism", "risk allele",
        "risk variant", "gwas", "genome-wide", "mutation", "mutations",
        "exome sequencing", "missense variant", "loss of function"
    ]):
        return "genetic_association"

    if any(phrase in text_lower for phrase in [
        "drug target", "drug targets", "antidiabetic drug target",
        "antidiabetic drug targets", "therapeutic target", "therapeutic targets",
        "inhibitor", "inhibitors", "agonist", "antagonist", "blocker",
        "targeted therapy", "pharmacological inhibition", "small molecule",
        "druggable", "therapeutic intervention"
    ]):
        return "drug_target"

    if any(phrase in text_lower for phrase in [
        "gene expression", "gene-expression", "expression level", "expression levels",
        "expression", "mrna", "transcription", "upregulation", "downregulation",
        "overexpression", "transcriptomic", "differential expression"
    ]):
        return "gene_expression"

    if any(phrase in text_lower for phrase in [
        "protein-protein interaction", "protein interaction", "ppi",
        "protein binding", "binding affinity", "complex formation",
        "interacts with", "co-immunoprecipitation", "crystallography"
    ]):
        return "protein_interaction"

    if any(phrase in text_lower for phrase in [
        "clinical trial", "clinical study", "patient cohort", "patients",
        "biomarker", "prognostic", "diagnostic", "plasma level", "serum level",
        "clinical efficacy", "therapeutic response"
    ]):
        return "clinical"

    if any(phrase in text_lower for phrase in [
        "mouse", "mice", "rat", "animal model", "animal models",
        "db/db", "knockout", "transgenic", "in vivo"
    ]):
        return "animal_model"

    if any(phrase in text_lower for phrase in [
        "cell", "cellular", "in vitro", "cell line", "assay",
        "pathway", "signaling", "mechanism", "functional study"
    ]):
        return "experimental"

    return "unknown"


def classify_relation(
    text: str,
    target_symbol: str,
    disease_name: str,
    synonyms: Optional[List[str]] = None
) -> str:
    text_lower = text.lower()
    target = target_symbol.lower()

    # ---------------------------------------------------------
    # Explicit negative relationship
    # ---------------------------------------------------------
    negative_patterns = [
        r"\bnot associated with\b",
        r"\bno significant association with\b",
        r"\bno association with\b",
        r"\bnot linked to\b",
        r"\bno significant relationship\b",
        r"\bno evidence\b",
        r"\bfailed to associate with\b",
        r"\bdid not associate with\b",
        r"\bno significant difference\b",
        r"\bnot correlated with\b",
    ]

    for pattern in negative_patterns:
        if re.search(pattern, text_lower):
            return "no_association"

    # ---------------------------------------------------------
    # Drug / Therapeutic target relationship
    # ---------------------------------------------------------
    drug_target_patterns = [
        "drug target", "drug targets", "antidiabetic drug target",
        "therapeutic target", "therapeutic targets", "therapeutic potential",
        "target for treatment", "potential target", "target for therapy",
        "inhibitor of", "agonist of", "treatment of"
    ]

    if any(term in text_lower for term in drug_target_patterns):
        return "drug_target_of"

    # ---------------------------------------------------------
    # Genetic association
    # ---------------------------------------------------------
    genetic_terms = [
        "genetic association", "genetic variant", "genetic variants",
        "single-nucleotide polymorphism", "single nucleotide polymorphism",
        "snp", "locus", "loci", "allele", "polymorphism", "risk allele",
        "risk variant", "gwas", "mutation"
    ]

    if any(term in text_lower for term in genetic_terms):
        if target in text_lower and contains_disease(text, disease_name, synonyms):
            return "associated_with"

    # ---------------------------------------------------------
    # Experimental / Mechanism relationship
    # ---------------------------------------------------------
    experimental_terms = [
        "expression", "upregulated", "downregulated", "increased expression",
        "decreased expression", "gene expression", "analyzed by quantitative pcr",
        "western blot", "knockdown", "overexpression", "pathway activation"
    ]

    animal_or_model_terms = [
        "mouse", "mice", "rat", "animal model", "db/db", "in vivo", "in vitro", "cells"
    ]

    if any(term in text_lower for term in experimental_terms) and any(term in text_lower for term in animal_or_model_terms):
        return "experimental_association"

    # ---------------------------------------------------------
    # Explicit association
    # ---------------------------------------------------------
    association_patterns = [
        r"\bassociated with\b",
        r"\bsignificant association\b",
        r"\bincreased risk\b",
        r"\bhigher risk\b",
        r"\brisk association\b",
        r"\blinked to\b",
        r"\bcorrelated with\b",
        r"\bplays a key role in\b",
        r"\bcontributes to\b",
        r"\binvolved in the pathogenesis\b",
        r"\bcritical for\b",
        r"\bmarker of\b",
        r"\bpromotes\b",
        r"\binhibits\b",
    ]

    for pattern in association_patterns:
        if re.search(pattern, text_lower):
            return "associated_with"

    # ---------------------------------------------------------
    # Fallback
    # ---------------------------------------------------------
    return "mentions"


def classify_evidence_strength(
    evidence_type: str,
    relation: str
) -> str:
    if relation == "no_association":
        return "strong"

    if evidence_type in ("genetic_association", "clinical"):
        return "strong"

    if evidence_type in ("drug_target", "animal_model", "experimental", "gene_expression", "protein_interaction"):
        return "moderate"

    return "weak"


def classify_direction(
    text: str,
    relation: str
) -> str:
    text_lower = text.lower()

    if relation == "no_association":
        return "negative_or_no_association"

    negative_patterns = [
        r"\bnot associated\b",
        r"\bno significant association\b",
        r"\bno association\b",
        r"\bnot linked\b",
        r"\bno evidence\b",
        r"\bno effect\b",
    ]

    for pattern in negative_patterns:
        if re.search(pattern, text_lower):
            return "negative_or_no_association"

    positive_patterns = [
        r"\bincreased risk\b",
        r"\bhigher risk\b",
        r"\brisk association\b",
        r"\bsignificant association\b",
        r"\bpositively associated\b",
        r"\bpromotes\b",
        r"\benhances\b",
        r"\btherapeutic target\b",
        r"\beffective\b",
        r"\bimproved\b",
        r"\bprotective\b",
    ]

    for pattern in positive_patterns:
        if re.search(pattern, text_lower):
            return "positive_association"

    return "unknown"