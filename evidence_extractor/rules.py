import re


def contains_disease(text: str, disease_name: str) -> bool:
    if not text or not disease_name:
        return False

    text_lower = text.lower()
    disease_lower = disease_name.strip().lower()

    disease_terms = {
        disease_lower,
        "type 2 diabetes",
        "type 2 diabetes mellitus",
        "t2dm",
        "t2d",
        "diabetes mellitus",
    }

    return any(
        term in text_lower
        for term in disease_terms
    )


def contains_target(text: str, target_symbol: str) -> bool:
    if not text or not target_symbol:
        return False

    pattern = rf"\b{re.escape(target_symbol)}\b"

    return bool(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )
    )


def classify_evidence_type(text: str) -> str:

    text_lower = text.lower()

    if any(
        phrase in text_lower
        for phrase in [
            "genetic association",
            "genetic variant",
            "genetic variants",
            "single-nucleotide polymorphism",
            "single nucleotide polymorphism",
            "snp",
            "locus",
            "loci",
            "allele",
            "polymorphism",
            "risk allele",
            "risk variant",
        ]
    ):
        return "genetic_association"

    if any(
        phrase in text_lower
        for phrase in [
            "gene expression",
            "gene-expression",
            "expression level",
            "expression",
            "mrna",
            "transcription",
        ]
    ):
        return "gene_expression"

    if any(
        phrase in text_lower
        for phrase in [
            "protein-protein interaction",
            "protein interaction",
            "ppi",
            "protein binding",
        ]
    ):
        return "protein_interaction"

    if any(
        phrase in text_lower
        for phrase in [
            "drug target",
            "drug targets",
            "antidiabetic drug target",
            "antidiabetic drug targets",
            "therapeutic target",
            "therapeutic targets",
        ]
    ):
        return "drug_target"

    if any(
        phrase in text_lower
        for phrase in [
            "mouse",
            "mice",
            "rat",
            "animal model",
            "animal models",
            "db/db",
        ]
    ):
        return "animal_model"

    if any(
        phrase in text_lower
        for phrase in [
            "cell",
            "cellular",
            "in vitro",
            "in vivo",
            "cell line",
        ]
    ):
        return "experimental"

    return "unknown"


def classify_relation(
    text: str,
    target_symbol: str,
    disease_name: str
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
    ]

    for pattern in negative_patterns:
        if re.search(pattern, text_lower):
            return "no_association"

    # ---------------------------------------------------------
    # Genetic association
    # ---------------------------------------------------------

    genetic_terms = [
        "genetic association",
        "genetic variant",
        "genetic variants",
        "single-nucleotide polymorphism",
        "single nucleotide polymorphism",
        "snp",
        "locus",
        "loci",
        "allele",
        "polymorphism",
        "risk allele",
        "risk variant",
    ]

    if any(
        term in text_lower
        for term in genetic_terms
    ):
        if (
            target in text_lower
            and contains_disease(text, disease_name)
        ):
            return "associated_with"

    # ---------------------------------------------------------
    # Drug target relationship
    # ---------------------------------------------------------

    drug_target_patterns = [
        "drug target",
        "drug targets",
        "antidiabetic drug target",
        "antidiabetic drug targets",
        "therapeutic target",
        "therapeutic targets",
    ]

    if any(
        term in text_lower
        for term in drug_target_patterns
    ):
        return "drug_target_of"

    # ---------------------------------------------------------
    # Experimental relationship
    # ---------------------------------------------------------

    experimental_terms = [
        "expression",
        "upregulated",
        "downregulated",
        "increased expression",
        "decreased expression",
        "gene expression",
        "analyzed by quantitative pcr",
    ]

    animal_terms = [
        "mouse",
        "mice",
        "rat",
        "animal model",
        "db/db",
    ]

    if (
        any(
            term in text_lower
            for term in experimental_terms
        )
        and any(
            term in text_lower
            for term in animal_terms
        )
    ):
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

    if evidence_type == "genetic_association":
        return "strong"

    if evidence_type == "drug_target":
        return "moderate"

    if evidence_type == "animal_model":
        return "moderate"

    if evidence_type == "experimental":
        return "moderate"

    if evidence_type == "gene_expression":
        return "moderate"

    if evidence_type == "protein_interaction":
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
    ]

    for pattern in positive_patterns:
        if re.search(pattern, text_lower):
            return "positive_association"

    return "unknown"