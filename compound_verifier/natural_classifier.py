"""
natural_classifier.py
---------------------
Natural origin classification engine for Step 7.

Distinguishes between:
  1. Natural Products (isolated from plants, fungi, marine, or microbial sources)
  2. Semi-synthetic / Natural Derivatives (chemically modified natural scaffolds)
  3. Synthetic Entities (purely man-made pharmaceutical small molecules)
  4. Unverified Compounds (indeterminate origin)

Includes an extensive curated taxonomy of phytochemical superclasses and subclasses,
cross-database signals (ChEMBL, PubChem), and synthetic drug registries.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from .models import NaturalOriginStatus, NaturalOriginVerification

# ---------------------------------------------------------------------------
# Tier 1: Curated Phytochemical Knowledge Base
# Mapping: normalized compound name -> (superclass, subclass, typical botanical/natural source)
# ---------------------------------------------------------------------------

_CURATED_NATURAL_PRODUCTS: Dict[str, Tuple[str, str, str]] = {
    # Flavonols
    "quercetin": ("Flavonoid", "Flavonol", "Found in onions, apples, berries, and Ginkgo biloba"),
    "rutin": ("Flavonoid", "Flavonol glycoside", "Found in buckwheat, citrus fruits, and tea"),
    "kaempferol": ("Flavonoid", "Flavonol", "Found in kale, beans, tea, and spinach"),
    "myricetin": ("Flavonoid", "Flavonol", "Found in berries, vegetables, and walnuts"),
    "fisetin": ("Flavonoid", "Flavonol", "Found in strawberries, apples, and persimmons"),
    "morin": ("Flavonoid", "Flavonol", "Found in Moraceae family plants (white mulberry)"),
    "isorhamnetin": ("Flavonoid", "Flavonol", "Found in Hippophae rhamnoides (sea buckthorn)"),

    # Flavones
    "apigenin": ("Flavonoid", "Flavone", "Found in chamomile, parsley, and celery"),
    "luteolin": ("Flavonoid", "Flavone", "Found in celery, broccoli, and green peppers"),
    "chrysin": ("Flavonoid", "Flavone", "Found in honey, propolis, and passion flowers"),
    "baicalein": ("Flavonoid", "Flavone", "Found in Scutellaria baicalensis (Chinese skullcap)"),
    "baicalin": ("Flavonoid", "Flavone glycoside", "Major glucuronide from Scutellaria baicalensis"),
    "wogonin": ("Flavonoid", "Flavone", "Found in Scutellaria baicalensis"),
    "diosmin": ("Flavonoid", "Flavone glycoside", "Citrus-derived flavonoid"),
    "tangeretin": ("Flavonoid", "Polymethoxylated flavone", "Found in citrus peels"),
    "nobiletin": ("Flavonoid", "Polymethoxylated flavone", "Found in citrus peels"),

    # Flavanones
    "naringenin": ("Flavonoid", "Flavanone", "Abundant in grapefruit and citrus fruits"),
    "naringin": ("Flavonoid", "Flavanone glycoside", "Major bitter glycoside in grapefruit"),
    "hesperetin": ("Flavonoid", "Flavanone", "Found in sweet oranges and lemons"),
    "hesperidin": ("Flavonoid", "Flavanone glycoside", "Predominant flavonoid in orange peels"),

    # Isoflavones
    "genistein": ("Flavonoid", "Isoflavone", "Major phytoestrogen from Glycine max (soybean)"),
    "daidzein": ("Flavonoid", "Isoflavone", "Phytoestrogen from soybeans and red clover"),
    "glycitein": ("Flavonoid", "Isoflavone", "Isoflavone component of soy"),
    "formononetin": ("Flavonoid", "Isoflavone", "Found in Trifolium pratense (red clover)"),
    "biochanin a": ("Flavonoid", "Isoflavone", "Found in red clover and cabbage"),
    "puerarin": ("Flavonoid", "Isoflavone glycoside", "Major isoflavone from Pueraria lobata (kudzu)"),

    # Flavan-3-ols / Catechins
    "catechin": ("Flavonoid", "Flavan-3-ol", "Found in Camellia sinensis (green tea) and cocoa"),
    "epicatechin": ("Flavonoid", "Flavan-3-ol", "Found in green tea, dark chocolate, and apples"),
    "epigallocatechin": ("Flavonoid", "Flavan-3-ol", "Green tea constituent"),
    "epigallocatechin gallate": ("Flavonoid", "Flavan-3-ol gallate", "Major antioxidant catechin in green tea (EGCG)"),
    "egcg": ("Flavonoid", "Flavan-3-ol gallate", "Major antioxidant polyphenol in green tea"),
    "theaflavin": ("Flavonoid", "Theaflavin", "Polyphenol formed during black tea fermentation"),

    # Stilbenoids & Polyphenols
    "resveratrol": ("Polyphenol", "Stilbenoid", "Phytoalexin found in grape skins, peanuts, and Polygonum cuspidatum"),
    "pterostilbene": ("Polyphenol", "Stilbenoid", "Natural dimethylated analog of resveratrol from blueberries"),
    "piceatannol": ("Polyphenol", "Stilbenoid", "Stilbenoid found in grapes, passion fruit, and white tea"),
    "curcumin": ("Polyphenol", "Curcuminoid", "Principal bioactive diarylheptanoid from Curcuma longa (turmeric)"),
    "demethoxycurcumin": ("Polyphenol", "Curcuminoid", "Minor curcuminoid from Curcuma longa"),
    "bisdemethoxycurcumin": ("Polyphenol", "Curcuminoid", "Curcuminoid component of turmeric rhizomes"),

    # Alkaloids
    "berberine": ("Alkaloid", "Isoquinoline alkaloid", "Bioactive alkaloid from Berberis, Coptis chinensis, and Hydrastis"),
    "coptisine": ("Alkaloid", "Isoquinoline alkaloid", "Alkaloid from Coptis chinensis"),
    "palmatine": ("Alkaloid", "Isoquinoline alkaloid", "Alkaloid found in Coptis and Berberis species"),
    "piperine": ("Alkaloid", "Piperidine alkaloid", "Pungent alkaloid from Piper nigrum (black pepper)"),
    "capsaicin": ("Alkaloid", "Capsaicinoid", "Active vanilloid component of Capsicum chili peppers"),
    "colchicine": ("Alkaloid", "Tropolone alkaloid", "Natural toxic alkaloid from Colchicum autumnale (autumn crocus)"),
    "vinblastine": ("Alkaloid", "Vinca alkaloid", "Vinca alkaloid from Catharanthus roseus (Madagascar periwinkle)"),
    "vincristine": ("Alkaloid", "Vinca alkaloid", "Anti-mitotic alkaloid from Catharanthus roseus"),
    "camptothecin": ("Alkaloid", "Quinoline alkaloid", "Cytotoxic alkaloid from Camptotheca acuminata (happy tree)"),
    "berbamine": ("Alkaloid", "Bisbenzylisoquinoline", "Alkaloid isolated from Berberis amurensis"),
    "tetrandrine": ("Alkaloid", "Bisbenzylisoquinoline", "Alkaloid from Stephania tetrandra"),

    # Terpenoids & Terpenes
    "artemisinin": ("Terpenoid", "Sesquiterpene lactone", "Antimalarial endoperoxide from Artemisia annua (sweet wormwood)"),
    "andrographolide": ("Terpenoid", "Diterpenoid lactone", "Extracted from Andrographis paniculata (King of Bitters)"),
    "ursolic acid": ("Terpenoid", "Pentacyclic triterpenoid", "Found in apple peels, rosemary, and holy basil (Ocimum sanctum)"),
    "oleanolic acid": ("Terpenoid", "Pentacyclic triterpenoid", "Found in Olea europaea (olive leaves) and Phytolacca"),
    "betulinic acid": ("Terpenoid", "Pentacyclic triterpenoid", "Lupane-type triterpenoid from Betula alba (birch bark)"),
    "betulin": ("Terpenoid", "Pentacyclic triterpenoid", "Precursor to betulinic acid from birch bark"),
    "lupeol": ("Terpenoid", "Pentacyclic triterpenoid", "Pharmacologically active triterpene from mango and dandelion"),
    "menthol": ("Terpenoid", "Monoterpenoid", "Organic monoterpene from Mentha piperita (peppermint)"),
    "thymol": ("Terpenoid", "Monoterpenoid phenol", "Natural monoterpene from Thymus vulgaris (thyme)"),
    "carvacrol": ("Terpenoid", "Monoterpenoid phenol", "Component of Origanum vulgare (oregano) oil"),
    "eugenol": ("Phenylpropanoid", "Allylbenzene", "Principal essential oil component of Syzygium aromaticum (cloves)"),
    "borneol": ("Terpenoid", "Bicyclic monoterpene", "Natural bicyclic terpene from Dryobalanops aromatica"),
    "geraniol": ("Terpenoid", "Monoterpenoid alcohol", "Found in rose oil and citronella"),

    # Phenolic Acids
    "chlorogenic acid": ("Phenolic Acid", "Hydroxycinnamic acid ester", "Major dietary polyphenol in green coffee beans"),
    "caffeic acid": ("Phenolic Acid", "Hydroxycinnamic acid", "Synthesized in plants by the phenylpropanoid pathway"),
    "ferulic acid": ("Phenolic Acid", "Hydroxycinnamic acid", "Abundant antioxidant in cell walls of grains and oats"),
    "gallic acid": ("Phenolic Acid", "Trihydroxybenzoic acid", "Found in gallnuts, tea leaves, and oak bark"),
    "ellagic acid": ("Polyphenol", "Ellagitannin derivative", "Dimeric gallic acid derivative from pomegranates and strawberries"),
    "rosmarinic acid": ("Phenolic Acid", "Caffeic acid ester", "Bioactive ester in Rosmarinus officinalis (rosemary)"),
    "protocatechuic acid": ("Phenolic Acid", "Dihydroxybenzoic acid", "Metabolite found in green tea and rooibos"),

    # Anthraquinones & Quinones
    "emodin": ("Anthraquinone", "Trihydroxyanthraquinone", "Isolated from Rheum palmatum (rhubarb) and Polygonum"),
    "aloe-emodin": ("Anthraquinone", "Trihydroxyanthraquinone", "Derived from Aloe vera latex"),
    "rhein": ("Anthraquinone", "Trihydroxyanthraquinone", "Bioactive compound in Rheum and Senna species"),
    "thymoquinone": ("Quinone", "Monoterpenoid quinone", "Primary active constituent of Nigella sativa (black seed)"),
    "tanshinone": ("Diterpenoid", "Diterpene quinone", "Lipophilic constituent of Salvia miltiorrhiza (Danshen)"),
    "cryptotanshinone": ("Diterpenoid", "Diterpene quinone", "Bioactive abietane diterpenoid from Salvia miltiorrhiza"),

    # Xanthones & Lignans
    "alpha-mangostin": ("Xanthone", "Prenylated xanthone", "Dominant xanthone in Garcinia mangostana (mangosteen)"),
    "gamma-mangostin": ("Xanthone", "Prenylated xanthone", "Antioxidant xanthone from Garcinia mangostana pericarp"),
    "honokiol": ("Lignan", "Neolignan", "Bioactive compound from Magnolia grandiflora / officinalis bark"),
    "magnolol": ("Lignan", "Neolignan", "Biphenolic neolignan from Magnolia officinalis bark"),
    "silymarin": ("Flavonolignan", "Flavonolignan complex", "Standardized milk thistle extract from Silybum marianum"),
    "silibinin": ("Flavonolignan", "Flavonolignan", "Primary active component of silymarin from milk thistle"),

    # Withanolides & Steroids
    "withaferin a": ("Steroid", "Withanolide", "Ergostane-type withanolide from Withania somnifera (Ashwagandha)"),
    "withanolide": ("Steroid", "Withanolide", "Steroidal lactone from Withania somnifera"),
    "ginsenoside": ("Steroid", "Triterpenoid saponin", "Dammarane-type saponins from Panax ginseng"),
    "guggulsterone": ("Steroid", "Phytosteroid", "Plant steroid from Commiphora mukul"),

    # Carotenoids & Coenzymes
    "lycopene": ("Carotenoid", "Tetraterpene", "Bright red carotene pigment in tomatoes and watermelons"),
    "astaxanthin": ("Carotenoid", "Xanthophyll", "Keto-carotenoid from Haematococcus pluvialis microalgae"),
    "lutein": ("Carotenoid", "Xanthophyll", "Naturally occurring carotenoid found in marigolds and green leafy vegetables"),
    "coenzyme q10": ("Quinone", "Ubiquinone", "Endogenous lipid-soluble antioxidant and mitochondrial cofactor"),
    "ubiquinol": ("Quinone", "Ubiquinol", "Reduced antioxidant electron-rich form of CoQ10"),

    # Organosulfur Compounds
    "allicin": ("Organosulfur", "Thiosulfinate", "Organosulfur defense compound from crushed Allium sativum (garlic)"),
    "alliin": ("Organosulfur", "Sulfoxide", "Natural amino acid precursor to allicin in garlic"),
    "sulforaphane": ("Organosulfur", "Isothiocyanate", "Derived from glucoraphanin in broccoli and cruciferous sprouts"),
    "indole-3-carbinol": ("Glucosinolate", "Indole derivative", "Produced by the breakdown of glucobrassicin in brassica vegetables"),

    # Ginger constituents
    "gingerol": ("Phenolic", "Vanilloid gingerol", "Pungent phytochemical in fresh Zingiber officinale (ginger) rhizome"),
    "shogaol": ("Phenolic", "Dehydrated gingerol", "Formed upon drying or heating ginger"),
}

# ---------------------------------------------------------------------------
# Tier 2: Curated Synthetic Pharmaceuticals & Small Molecules
# Mapping: normalized name -> (pharmacological class, clinical purpose)
# ---------------------------------------------------------------------------

_CURATED_SYNTHETICS: Dict[str, Tuple[str, str]] = {
    # Antidiabetic synthetics
    "metformin": ("Biguanide", "Synthetic antidiabetic agent; first-line T2DM therapy"),
    "phenformin": ("Biguanide", "Synthetic biguanide oral antihyperglycemic"),
    "glibenclamide": ("Sulfonylurea", "Second-generation synthetic sulfonylurea K_ATP blocker"),
    "glyburide": ("Sulfonylurea", "Second-generation synthetic sulfonylurea"),
    "glipizide": ("Sulfonylurea", "Second-generation synthetic sulfonylurea secretagogue"),
    "glimepiride": ("Sulfonylurea", "Third-generation synthetic sulfonylurea"),
    "tolbutamide": ("Sulfonylurea", "First-generation synthetic sulfonylurea"),
    "gliclazide": ("Sulfonylurea", "Synthetic sulfonylurea oral hypoglycemic"),
    "rosiglitazone": ("Thiazolidinedione", "Synthetic PPAR-gamma agonist antidiabetic"),
    "pioglitazone": ("Thiazolidinedione", "Synthetic PPAR-gamma agonist oral antidiabetic"),
    "troglitazone": ("Thiazolidinedione", "Synthetic first-generation thiazolidinedione"),
    "sitagliptin": ("DPP-4 Inhibitor", "Synthetic dipeptidyl peptidase-4 enzyme inhibitor"),
    "vildagliptin": ("DPP-4 Inhibitor", "Synthetic DPP-4 inhibitor antidiabetic"),
    "saxagliptin": ("DPP-4 Inhibitor", "Synthetic cyanopyrrolidine DPP-4 inhibitor"),
    "linagliptin": ("DPP-4 Inhibitor", "Synthetic xanthine-based DPP-4 inhibitor"),
    "dapagliflozin": ("SGLT2 Inhibitor", "Synthetic sodium-glucose cotransporter 2 inhibitor"),
    "empagliflozin": ("SGLT2 Inhibitor", "Synthetic SGLT2 inhibitor for glycemic control"),
    "canagliflozin": ("SGLT2 Inhibitor", "Synthetic SGLT2 inhibitor"),

    # Synthetic Kinase Inhibitors & Targeted Oncology
    "imatinib": ("Kinase Inhibitor", "Synthetic 2-phenylaminopyrimidine BCR-ABL tyrosine kinase inhibitor"),
    "erlotinib": ("Kinase Inhibitor", "Synthetic EGFR tyrosine kinase inhibitor"),
    "gefitinib": ("Kinase Inhibitor", "Synthetic anilinoquinazoline EGFR inhibitor"),
    "sorafenib": ("Kinase Inhibitor", "Synthetic multi-kinase inhibitor (VEGFR, PDGFR, Raf)"),
    "sunitinib": ("Kinase Inhibitor", "Synthetic multi-targeted receptor tyrosine kinase inhibitor"),
    "dabrafenib": ("Kinase Inhibitor", "Synthetic mutant BRAF V600 inhibitor"),
    "lapatinib": ("Kinase Inhibitor", "Synthetic dual EGFR/HER2 tyrosine kinase inhibitor"),
    "ibrutinib": ("Kinase Inhibitor", "Synthetic Bruton tyrosine kinase (BTK) covalent inhibitor"),

    # Cardiovascular & Statins
    "atorvastatin": ("Synthetic Statin", "Synthetic HMG-CoA reductase inhibitor"),
    "rosuvastatin": ("Synthetic Statin", "Synthetic enantiopure fluorinated statin"),
    "fluvastatin": ("Synthetic Statin", "First fully synthetic HMG-CoA reductase inhibitor"),
    "amlodipine": ("Dihydropyridine", "Synthetic L-type calcium channel blocker"),
    "lisinopril": ("ACE Inhibitor", "Synthetic dicarboxylic acid-containing ACE inhibitor"),
    "losartan": ("ARB", "Synthetic imidazole-derived angiotensin II receptor antagonist"),

    # Anti-inflammatory & Analgesics
    "ibuprofen": ("NSAID", "Synthetic propionic acid derivative COX-1/COX-2 inhibitor"),
    "acetaminophen": ("Analgesic", "Synthetic p-aminophenol derivative analgesic/antipyretic"),
    "paracetamol": ("Analgesic", "Synthetic p-aminophenol derivative"),
    "celecoxib": ("NSAID (Coxib)", "Synthetic selective COX-2 inhibitor"),
    "diclofenac": ("NSAID", "Synthetic phenylacetic acid derivative NSAID"),
    "naproxen": ("NSAID", "Synthetic propionic acid derivative NSAID"),
    "methotrexate": ("Antimetabolite", "Synthetic folic acid antagonist and immunosuppressant"),
}

# ---------------------------------------------------------------------------
# Tier 3: Curated Semi-Synthetic Derivatives (Natural Derivatives)
# ---------------------------------------------------------------------------

_CURATED_NATURAL_DERIVATIVES: Dict[str, Tuple[str, str, str]] = {
    "aspirin": (
        "Natural Derivative",
        "Salicylate derivative",
        "Acetyl derivative of naturally occurring salicylic acid (originally from Salix alba willow bark)"
    ),
    "dihydroartemisinin": (
        "Natural Derivative",
        "Semi-synthetic Artemisinin",
        "Active metabolite and semi-synthetic lactone derivative of Artemisia annua artemisinin"
    ),
    "artemether": (
        "Natural Derivative",
        "Semi-synthetic Artemisinin",
        "Methyl ether derivative of dihydroartemisinin"
    ),
    "artesunate": (
        "Natural Derivative",
        "Semi-synthetic Artemisinin",
        "Water-soluble hemisuccinate derivative of dihydroartemisinin"
    ),
    "docetaxel": (
        "Natural Derivative",
        "Taxane derivative",
        "Semi-synthetic taxoid analog of paclitaxel derived from 10-deacetylbaccatin III"
    ),
    "pravastatin": (
        "Natural Derivative",
        "Derived Statin",
        "Derived by microbiological hydroxylation of mevastatin (compactin)"
    ),
    "simvastatin": (
        "Natural Derivative",
        "Derived Statin",
        "Semi-synthetic derivative of fungal fermentation product lovastatin"
    ),
}


class NaturalOriginClassifier:
    """
    Classifier to evaluate compound identity and provenance against
    curated phytochemical registries, synthetic drug databases, and ChEMBL flags.
    """

    @classmethod
    def classify(
        cls,
        name: str,
        synonyms: Optional[List[str]] = None,
        chembl_meta: Optional[Dict[str, Any]] = None,
        retrieval_routes: Optional[List[str]] = None,
        is_chembl_natural: Optional[bool] = None,
    ) -> NaturalOriginVerification:
        """
        Classify candidate compound into Natural, Natural Derivative, or Synthetic origin.

        Parameters
        ----------
        name : Primary compound name
        synonyms : Chemical synonyms
        chembl_meta : Optional raw ChEMBL molecule dictionary
        retrieval_routes : Step 6 retrieval routes (e.g. 'disease_natural_literature')
        is_chembl_natural : Explicit boolean from ChEMBL 'natural_product' property
        """
        norm_name = cls._normalize(name)
        candidate_names = [norm_name]
        if synonyms:
            for s in synonyms:
                clean_s = cls._normalize(s)
                if clean_s and clean_s not in candidate_names:
                    candidate_names.append(clean_s)

        # ---------------------------------------------------------------------
        # 1. Match against Curated Semi-Synthetic / Natural Derivatives
        # ---------------------------------------------------------------------
        for cname in candidate_names:
            if cname in _CURATED_NATURAL_DERIVATIVES:
                superclass, subclass, notes = _CURATED_NATURAL_DERIVATIVES[cname]
                return NaturalOriginVerification(
                    status=NaturalOriginStatus.NATURAL_DERIVATIVE,
                    is_natural=True,
                    confidence=0.95,
                    natural_product_class=superclass,
                    subclass=subclass,
                    determination_method="curated_natural_derivative_registry",
                    evidence_sources=["Curated_Natural_Registry"],
                    notes=notes,
                )

        # ---------------------------------------------------------------------
        # 2. Match against Curated Natural Products
        # ---------------------------------------------------------------------
        for cname in candidate_names:
            if cname in _CURATED_NATURAL_PRODUCTS:
                superclass, subclass, notes = _CURATED_NATURAL_PRODUCTS[cname]
                sources = ["Curated_Natural_Registry"]
                if is_chembl_natural:
                    sources.append("ChEMBL")

                return NaturalOriginVerification(
                    status=NaturalOriginStatus.NATURAL,
                    is_natural=True,
                    confidence=0.98 if is_chembl_natural else 0.95,
                    natural_product_class=superclass,
                    subclass=subclass,
                    determination_method="curated_phytochemical_registry",
                    evidence_sources=sources,
                    notes=notes,
                )

        # ---------------------------------------------------------------------
        # 3. Match against Curated Synthetics
        # ---------------------------------------------------------------------
        for cname in candidate_names:
            if cname in _CURATED_SYNTHETICS:
                pharm_class, notes = _CURATED_SYNTHETICS[cname]
                return NaturalOriginVerification(
                    status=NaturalOriginStatus.SYNTHETIC,
                    is_natural=False,
                    confidence=0.98,
                    natural_product_class="Synthetic",
                    subclass=pharm_class,
                    determination_method="curated_synthetic_registry",
                    evidence_sources=["Curated_Synthetic_Registry"],
                    notes=notes,
                )

        # ---------------------------------------------------------------------
        # 4. Check ChEMBL metadata & flags
        # ---------------------------------------------------------------------
        if is_chembl_natural:
            return NaturalOriginVerification(
                status=NaturalOriginStatus.NATURAL,
                is_natural=True,
                confidence=0.88,
                natural_product_class="Natural Product (ChEMBL Certified)",
                subclass=None,
                determination_method="chembl_natural_product_flag",
                evidence_sources=["ChEMBL"],
                notes="Flagged as Natural Product in EMBL-EBI ChEMBL Database",
            )

        if chembl_meta:
            mol_type = (chembl_meta.get("molecule_type") or "").lower()
            if "natural" in mol_type:
                return NaturalOriginVerification(
                    status=NaturalOriginStatus.NATURAL,
                    is_natural=True,
                    confidence=0.85,
                    natural_product_class="Natural Product",
                    subclass=None,
                    determination_method="chembl_molecule_type",
                    evidence_sources=["ChEMBL"],
                    notes="Molecule type listed as Natural Product in ChEMBL",
                )
            elif "synthetic" in mol_type or mol_type == "small molecule":
                # ChEMBL 'Small molecule' without natural_product flag is frequently synthetic
                if is_chembl_natural is False and not (retrieval_routes and "disease_natural_literature" in retrieval_routes):
                    return NaturalOriginVerification(
                        status=NaturalOriginStatus.SYNTHETIC,
                        is_natural=False,
                        confidence=0.72,
                        natural_product_class="Synthetic Small Molecule",
                        subclass=None,
                        determination_method="chembl_annotation_heuristic",
                        evidence_sources=["ChEMBL"],
                        notes="ChEMBL small molecule with no certified natural origin flag",
                    )

        # ---------------------------------------------------------------------
        # 5. Heuristic: Retrieval Route Evidence
        # ---------------------------------------------------------------------
        if retrieval_routes and "disease_natural_literature" in retrieval_routes:
            # Sourced via specific natural-product literature mining
            return NaturalOriginVerification(
                status=NaturalOriginStatus.NATURAL,
                is_natural=True,
                confidence=0.70,
                natural_product_class="Suspected Natural Product",
                subclass=None,
                determination_method="literature_natural_mining_route",
                evidence_sources=["PubMed_Literature_Route_A"],
                notes="Identified in literature context explicitly discussing natural products and phytotherapy",
            )

        # ---------------------------------------------------------------------
        # 6. Default: Unverified
        # ---------------------------------------------------------------------
        return NaturalOriginVerification(
            status=NaturalOriginStatus.UNVERIFIED,
            is_natural=False,
            confidence=0.30,
            natural_product_class="Unclassified",
            subclass=None,
            determination_method="indeterminate",
            evidence_sources=[],
            notes="Origin could not be conclusively determined from available registries or database flags",
        )

    @staticmethod
    def _normalize(text: Optional[str]) -> str:
        """Standardize compound name for robust string matching."""
        if not text:
            return ""
        # Lowercase, replace hyphens/underscores with space, strip extra whitespace
        cleaned = text.lower().strip()
        cleaned = re.sub(r"[\-_]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

