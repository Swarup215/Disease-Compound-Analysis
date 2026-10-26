"""
retriever.py
------------
Step 6: Natural Compound Candidate Retrieval

Implements the two-route retrieval strategy from the pipeline architecture:

  Route A  Disease --> Natural Compounds
           PubMed queries with disease name + natural-product keywords.
           Mines abstracts to extract candidate compound names and snippets.

  Route B  Protein --> Compounds
           ChEMBL bioactivity data for each prioritized protein target
           (resolved via ChEMBL target API using gene symbol / UniProt ID).
           Supplemented by target-specific PubMed literature.

Both routes run independently; results are merged by compound identity
(InChIKey > ChEMBL ID > name normalisation) so that compounds found by
both routes are flagged as dual-route hits.

The compound-target relationship and source evidence (PMID/snippet) are
captured *at retrieval time* and stored in CompoundCandidate.target_relations
for provenance — no separate extraction stage is needed.
"""

import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from .chembl_client import ChEMBLClient
from .models import (
    BioactivityRecord,
    CompoundCandidate,
    CompoundRetrievalResult,
    TargetRelation,
)
from .pubmed_compound import PubMedCompoundClient

# ---------------------------------------------------------------------------
# Named-compound extraction from free text
# ---------------------------------------------------------------------------

# Patterns for recognisable chemical / phytochemical names in text.
# We anchor on a curated list of common natural-product classes and specific
# well-known compounds so we don't blindly extract every capitalised noun.
_NP_COMPOUND_NAMES = [
    "quercetin", "rutin", "kaempferol", "apigenin", "luteolin", "fisetin",
    "myricetin", "morin", "naringenin", "naringin", "hesperidin", "hesperetin",
    "diosmin", "tangeretin", "nobiletin", "baicalein", "baicalin", "wogonin",
    "chrysin", "genistein", "daidzein", "glycitein", "formononetin",
    "biochanin a", "prunetin", "catechin", "epicatechin", "epigallocatechin",
    "epigallocatechin gallate", "egcg", "theaflavin", "thearubigin",
    "resveratrol", "piceatannol", "pterostilbene", "oxyresveratrol",
    "curcumin", "demethoxycurcumin", "bisdemethoxycurcumin",
    "berberine", "coptisine", "palmatine", "jatrorrhizine",
    "colchicine", "vinblastine", "vincristine", "camptothecin",
    "paclitaxel", "taxol", "docetaxel",
    "silymarin", "silibinin", "silychristin", "silydianin",
    "ellagic acid", "gallic acid", "protocatechuic acid",
    "chlorogenic acid", "caffeic acid", "ferulic acid", "p-coumaric acid",
    "rosmarinic acid", "ursolic acid", "oleanolic acid", "betulinic acid",
    "betulin", "lupeol", "alpha-mangostin", "gamma-mangostin",
    "andrographolide", "artemisin", "artemisinin", "dihydroartemisinin",
    "piperine", "capsaicin", "gingerol", "zingerone", "shogaol",
    "thymoquinone", "carvacrol", "thymol", "eugenol",
    "lycopene", "beta-carotene", "lutein", "zeaxanthin", "astaxanthin",
    "coenzyme q10", "ubiquinol",
    "allicin", "alliin", "s-allylcysteine",
    "menthol", "borneol", "camphor", "geraniol",
    "honokiol", "magnolol", "emodin", "aloe-emodin", "rhein", "chrysophanol",
    "hypericin", "hyperforin",
    "bakuchiol", "psoralen", "bergapten",
    "nobiletin", "polymethoxylated flavone",
    "ginsenoside", "panaxadiol", "panaxatriol",
    "withaferin a", "withanolide",
    "berbamine", "tetrandrine", "fangchinoline",
    "tanshinone", "cryptotanshinone", "dihydrotanshinone",
    "puerarin", "kudzu",
    "sulforaphane", "indole-3-carbinol", "3,3-diindolylmethane",
    "fucoxanthin", "fucosterol",
]

# Build a compiled pattern for fast multi-term search
_COMPOUND_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in _NP_COMPOUND_NAMES) + r")\b",
    re.IGNORECASE,
)


def _extract_compound_names_from_text(text: str) -> List[str]:
    """Return distinct compound names found in *text*."""
    return list({m.group(0).lower() for m in _COMPOUND_PATTERN.finditer(text)})


def _normalize_name(name: str) -> str:
    """Lowercase + collapse whitespace for key comparison."""
    return re.sub(r"\s+", " ", name.strip().lower())


def _best_potency_nM(bioactivities: List[BioactivityRecord]) -> Optional[float]:
    """Return the lowest IC50/Ki/Kd value expressed in nM, or None."""
    best: Optional[float] = None
    for act in bioactivities:
        if act.standard_value is None:
            continue
        units = (act.standard_units or "").strip().lower()
        val = act.standard_value
        # Convert to nM
        if units in ("nm", "nmol/l"):
            val_nm = val
        elif units in ("um", "umol/l", "\u03bcm", "\u03bcmol/l"):
            val_nm = val * 1000.0
        elif units in ("mm", "mmol/l"):
            val_nm = val * 1_000_000.0
        elif units in ("pm", "pmol/l"):
            val_nm = val / 1000.0
        else:
            continue  # unknown unit, skip
        if act.standard_type in ("IC50", "Ki", "Kd", "EC50"):
            if best is None or val_nm < best:
                best = val_nm
    return best


# ---------------------------------------------------------------------------
# Main Retriever Class
# ---------------------------------------------------------------------------


class NaturalCompoundRetriever:
    """
    Orchestrates Step 6: Natural Compound Candidate Retrieval.

    Parameters
    ----------
    pubmed_api_key : optional NCBI API key (raises rate limit from 3 to 10 req/s)
    max_route_a_papers : PubMed papers to process per Route A query
    max_route_b_activities : ChEMBL activity records per target
    max_route_b_papers : PubMed papers to process per Route B target query
    """

    def __init__(
        self,
        pubmed_api_key: Optional[str] = None,
        max_route_a_papers: int = 30,
        max_route_b_activities: int = 200,
        max_route_b_papers: int = 10,
    ):
        self.pubmed = PubMedCompoundClient(api_key=pubmed_api_key)
        self.chembl = ChEMBLClient()
        self.max_route_a_papers = max_route_a_papers
        self.max_route_b_activities = max_route_b_activities
        self.max_route_b_papers = max_route_b_papers

    # ==================================================================
    # Public entry point
    # ==================================================================

    def retrieve(
        self,
        disease_name: str,
        targets: Optional[List[Dict[str, Any]]] = None,
        disease_synonyms: Optional[List[str]] = None,
    ) -> CompoundRetrievalResult:
        """
        Run both retrieval routes and return a merged CompoundRetrievalResult.

        Parameters
        ----------
        disease_name  : canonical disease name (e.g. "type 2 diabetes mellitus")
        targets       : list of target dicts with keys: symbol, name, uniprot_id (opt)
        disease_synonyms : additional disease aliases to include in queries
        """
        targets = targets or []
        disease_synonyms = disease_synonyms or []

        # ------------------------------------------------------------------
        # Route A
        # ------------------------------------------------------------------
        route_a_compounds = self._route_a(disease_name, disease_synonyms)

        # ------------------------------------------------------------------
        # Route B
        # ------------------------------------------------------------------
        route_b_compounds = self._route_b(disease_name, targets)

        # ------------------------------------------------------------------
        # Merge both routes
        # ------------------------------------------------------------------
        merged = self._merge(route_a_compounds, route_b_compounds)

        # ------------------------------------------------------------------
        # Build result
        # ------------------------------------------------------------------
        target_symbols = [t.get("symbol", "") for t in targets if t.get("symbol")]
        route_a_ids: Set[str] = {c.compound_id for c in route_a_compounds}
        route_b_ids: Set[str] = {c.compound_id for c in route_b_compounds}

        dual_count = sum(
            1 for c in merged
            if c.compound_id in route_a_ids and c.compound_id in route_b_ids
        )

        return CompoundRetrievalResult(
            disease_name=disease_name,
            targets_queried=target_symbols,
            total_compounds=len(merged),
            route_a_count=len(route_a_ids),
            route_b_count=len(route_b_ids),
            dual_route_count=dual_count,
            compounds=merged,
        )

    # ==================================================================
    # Route A: Disease -> Natural Compounds via PubMed
    # ==================================================================

    def _route_a(
        self,
        disease_name: str,
        synonyms: List[str],
    ) -> List[CompoundCandidate]:
        """Search PubMed for natural compounds associated with the disease."""
        queries = self._build_route_a_queries(disease_name, synonyms)
        compounds_by_key: Dict[str, CompoundCandidate] = {}

        for query in queries:
            articles = self.pubmed.search_and_fetch(
                query, retmax=self.max_route_a_papers
            )
            for article in articles:
                # Extract compound names from title + abstract
                full_text = f"{article.get('title', '')} {article.get('abstract', '')}"
                found_names = _extract_compound_names_from_text(full_text)

                for cname in found_names:
                    key = _normalize_name(cname)
                    if key not in compounds_by_key:
                        compounds_by_key[key] = CompoundCandidate(
                            compound_id=f"LIT:{key.replace(' ', '_').upper()}",
                            name=cname.lower(),
                            natural_origin=True,
                            natural_origin_source="Literature",
                            retrieval_routes=["disease_natural_literature"],
                            evidence_sources=["PubMed"],
                        )

                    cand = compounds_by_key[key]

                    # Add PMID
                    pmid = article.get("pmid")
                    if pmid and pmid not in cand.provenance.get("pmids", []):
                        cand.provenance.setdefault("pmids", []).append(pmid)
                        cand.citation_count += 1

                    # Add snippet
                    for snippet in article.get("compound_snippets", []):
                        if snippet not in cand.provenance.get("snippets", []):
                            cand.provenance.setdefault("snippets", []).append(snippet)

                    # Ensure route is recorded
                    if "disease_natural_literature" not in cand.retrieval_routes:
                        cand.retrieval_routes.append("disease_natural_literature")

        return list(compounds_by_key.values())

    @staticmethod
    def _build_route_a_queries(disease_name: str, synonyms: List[str]) -> List[str]:
        """Build a small set of PubMed boolean queries for Route A."""
        disease_terms = [f'"{disease_name}"']
        for syn in synonyms[:2]:
            if syn and syn.lower() != disease_name.lower():
                disease_terms.append(f'"{syn}"')
        disease_expr = " OR ".join(disease_terms)

        # Core natural-product filter
        np_filter = (
            '("natural product" OR "natural compound" OR phytochemical OR '
            "flavonoid OR polyphenol OR alkaloid OR terpenoid OR "
            "curcumin OR berberine OR quercetin OR resveratrol)"
        )

        queries = [
            f"({disease_expr}) AND {np_filter}",
            f"({disease_expr}) AND (plant extract OR herbal medicine OR botanical)",
            f"({disease_expr}) AND (natural product[MeSH] OR phytotherapy[MeSH])",
        ]
        return queries

    # ==================================================================
    # Route B: Protein -> Compounds via ChEMBL + PubMed
    # ==================================================================

    def _route_b(
        self,
        disease_name: str,
        targets: List[Dict[str, Any]],
    ) -> List[CompoundCandidate]:
        """Query ChEMBL for bioactive compounds against each prioritized target."""
        compounds_by_key: Dict[str, CompoundCandidate] = {}

        for target in targets:
            symbol = target.get("symbol") or target.get("target_symbol") or ""
            uniprot_id = target.get("uniprot_id") or target.get("id") or ""
            target_name = target.get("name") or symbol

            if not symbol:
                continue

            # 1. Resolve ChEMBL target ID
            chembl_target_id = self._resolve_chembl_target(symbol, uniprot_id)
            if not chembl_target_id:
                # Fall through to literature-only for this target
                self._route_b_literature(
                    disease_name, symbol, target_name, compounds_by_key
                )
                continue

            # 2. Fetch bioactivity records
            activities = self.chembl.get_activities_for_target(
                target_chembl_id=chembl_target_id,
                max_results=self.max_route_b_activities,
            )

            if not activities:
                self._route_b_literature(
                    disease_name, symbol, target_name, compounds_by_key
                )
                continue

            # 3. Group activities by molecule
            by_molecule: Dict[str, List[Dict]] = {}
            for act in activities:
                mol_id = act.get("molecule_chembl_id") or ""
                if mol_id:
                    by_molecule.setdefault(mol_id, []).append(act)

            # 4. Fetch molecule metadata in batch (≤100 at a time)
            mol_ids = list(by_molecule.keys())
            mol_meta_list = self.chembl.get_molecules_batch(mol_ids[:100])
            mol_meta: Dict[str, Dict] = {
                m.get("molecule_chembl_id", ""): m for m in mol_meta_list
            }

            # 5. Build CompoundCandidate for each molecule
            for mol_id, mol_acts in by_molecule.items():
                meta = mol_meta.get(mol_id, {})
                cand = self._build_compound_from_chembl(
                    mol_id=mol_id,
                    mol_meta=meta,
                    mol_acts=mol_acts,
                    target_symbol=symbol,
                    target_name=target_name,
                    chembl_target_id=chembl_target_id,
                )
                key = cand.compound_id
                if key in compounds_by_key:
                    # Merge target relations
                    existing = compounds_by_key[key]
                    existing_symbols = {tr.target_symbol for tr in existing.target_relations}
                    for tr in cand.target_relations:
                        if tr.target_symbol not in existing_symbols:
                            existing.target_relations.append(tr)
                            existing.targets_targeted.append(tr.target_symbol)
                    # Update best bioactivity
                    if cand.best_bioactivity_nM is not None:
                        if (
                            existing.best_bioactivity_nM is None
                            or cand.best_bioactivity_nM < existing.best_bioactivity_nM
                        ):
                            existing.best_bioactivity_nM = cand.best_bioactivity_nM
                else:
                    compounds_by_key[key] = cand

            # 6. Complement with protein-specific PubMed literature
            self._route_b_literature(
                disease_name, symbol, target_name, compounds_by_key
            )

        return list(compounds_by_key.values())

    def _resolve_chembl_target(
        self,
        gene_symbol: str,
        uniprot_id: str,
    ) -> Optional[str]:
        """Try to resolve a ChEMBL target ID via UniProt or gene symbol."""
        if uniprot_id:
            cid = self.chembl.resolve_target_by_uniprot(uniprot_id)
            if cid:
                return cid
        return self.chembl.resolve_target_by_gene_name(gene_symbol)

    def _build_compound_from_chembl(
        self,
        mol_id: str,
        mol_meta: Dict,
        mol_acts: List[Dict],
        target_symbol: str,
        target_name: str,
        chembl_target_id: str,
    ) -> CompoundCandidate:
        """Construct a CompoundCandidate from ChEMBL molecule + activity data."""
        props = mol_meta.get("molecule_properties") or {}
        struct = mol_meta.get("molecule_structures") or {}
        pref_name = (
            mol_meta.get("pref_name")
            or mol_meta.get("molecule_chembl_id")
            or mol_id
        )

        # Build BioactivityRecord list
        bioact_records: List[BioactivityRecord] = []
        pmids: List[str] = []
        for act in mol_acts:
            rec = BioactivityRecord(
                activity_id=act.get("activity_id"),
                standard_type=act.get("standard_type", "Unknown"),
                standard_value=act.get("standard_value"),
                standard_units=act.get("standard_units"),
                standard_relation=act.get("standard_relation", "="),
                assay_type=act.get("assay_type"),
                assay_description=act.get("assay_description"),
                target_chembl_id=chembl_target_id,
                target_symbol=target_symbol,
                document_chembl_id=act.get("document_chembl_id"),
                pmid=act.get("pmid"),
                doi=act.get("doi"),
            )
            bioact_records.append(rec)
            if rec.pmid and rec.pmid not in pmids:
                pmids.append(rec.pmid)

        best_potency = _best_potency_nM(bioact_records)

        # Determine relation type from most-specific assay type
        act_types = {r.standard_type for r in bioact_records}
        if "Ki" in act_types or "Kd" in act_types:
            relation_type = "inhibitor"
        elif "EC50" in act_types:
            relation_type = "agonist"
        elif "IC50" in act_types:
            relation_type = "inhibitor"
        else:
            relation_type = "active_against"

        target_rel = TargetRelation(
            target_symbol=target_symbol,
            target_name=target_name,
            target_chembl_id=chembl_target_id,
            relation_type=relation_type,
            bioactivities=bioact_records,
            best_potency_nM=best_potency,
            pmids=pmids,
            source="ChEMBL",
        )

        is_natural = ChEMBLClient.is_natural_origin(mol_meta)

        # Synonyms from molecule
        synonyms_raw = mol_meta.get("molecule_synonyms") or []
        synonyms = [
            s.get("molecule_synonym", "")
            for s in synonyms_raw
            if s.get("molecule_synonym")
        ][:10]

        # PubChem CID (if stored in cross-references, best effort)
        pubchem_cid: Optional[int] = None
        for xref in (mol_meta.get("cross_references") or []):
            if xref.get("xref_src") == "PubChem" and xref.get("xref_id"):
                try:
                    pubchem_cid = int(xref["xref_id"])
                    break
                except (ValueError, TypeError):
                    pass

        return CompoundCandidate(
            compound_id=mol_id,
            name=pref_name.lower(),
            synonyms=synonyms,
            smiles=struct.get("canonical_smiles"),
            inchikey=struct.get("standard_inchi_key"),
            pubchem_cid=pubchem_cid,
            chembl_id=mol_id,
            natural_origin=is_natural,
            natural_origin_source="ChEMBL" if is_natural else None,
            retrieval_routes=["protein_chembl_bioactivity"],
            targets_targeted=[target_symbol],
            target_relations=[target_rel],
            evidence_sources=["ChEMBL"],
            citation_count=len(pmids),
            best_bioactivity_nM=best_potency,
            provenance={
                "chembl_target_id": chembl_target_id,
                "pmids": pmids,
                "activity_count": len(bioact_records),
            },
        )

    def _route_b_literature(
        self,
        disease_name: str,
        target_symbol: str,
        target_name: str,
        compounds_by_key: Dict[str, CompoundCandidate],
    ) -> None:
        """
        Supplement Route B with protein-specific PubMed to capture
        compounds not in ChEMBL.  Mutates *compounds_by_key* in-place.
        """
        query = (
            f'"{target_symbol}"[Title/Abstract] AND '
            f'("natural product" OR phytochemical OR flavonoid OR '
            f"curcumin OR berberine OR quercetin)"
        )
        articles = self.pubmed.search_and_fetch(
            query, retmax=self.max_route_b_papers
        )
        for article in articles:
            full_text = f"{article.get('title', '')} {article.get('abstract', '')}"
            found_names = _extract_compound_names_from_text(full_text)
            pmid = article.get("pmid")

            for cname in found_names:
                key = _normalize_name(cname)
                # Only update existing candidates or create new ones
                if key in compounds_by_key:
                    cand = compounds_by_key[key]
                else:
                    cand = CompoundCandidate(
                        compound_id=f"LIT:{key.replace(' ', '_').upper()}",
                        name=cname.lower(),
                        natural_origin=True,
                        natural_origin_source="Literature",
                        retrieval_routes=["protein_literature"],
                        evidence_sources=["PubMed"],
                    )
                    compounds_by_key[key] = cand

                # Add literature route if not already present
                if "protein_literature" not in cand.retrieval_routes:
                    cand.retrieval_routes.append("protein_literature")

                # Record PMID and snippet
                if pmid and pmid not in cand.provenance.get("pmids", []):
                    cand.provenance.setdefault("pmids", []).append(pmid)
                    cand.citation_count += 1

                for snippet in article.get("compound_snippets", []):
                    if snippet not in cand.provenance.get("snippets", []):
                        cand.provenance.setdefault("snippets", []).append(snippet)

                # Ensure target is tracked
                if target_symbol not in cand.targets_targeted:
                    cand.targets_targeted.append(target_symbol)

                # Add a minimal TargetRelation for literature-sourced links
                existing_tr_symbols = {tr.target_symbol for tr in cand.target_relations}
                if target_symbol not in existing_tr_symbols:
                    cand.target_relations.append(
                        TargetRelation(
                            target_symbol=target_symbol,
                            target_name=target_name,
                            relation_type="literature_mentioned",
                            pmids=[pmid] if pmid else [],
                            evidence_snippets=article.get("compound_snippets", [])[:3],
                            source="PubMed",
                        )
                    )

    # ==================================================================
    # Merge + deduplicate
    # ==================================================================

    @staticmethod
    def _merge(
        route_a: List[CompoundCandidate],
        route_b: List[CompoundCandidate],
    ) -> List[CompoundCandidate]:
        """
        Merge two compound lists, deduplicating by:
          1. InChIKey (most reliable)
          2. ChEMBL ID
          3. Normalised name

        When a compound appears in both routes, its retrieval_routes and
        evidence_sources are combined and evidence from both sources is merged.
        """
        merged: Dict[str, CompoundCandidate] = {}

        def _deduplicate_key(c: CompoundCandidate) -> str:
            if c.inchikey:
                return f"IK:{c.inchikey}"
            if c.chembl_id:
                return f"CID:{c.chembl_id}"
            return f"NAME:{_normalize_name(c.name)}"

        for cand in route_a + route_b:
            key = _deduplicate_key(cand)
            if key not in merged:
                merged[key] = cand
            else:
                existing = merged[key]
                # Merge routes
                for route in cand.retrieval_routes:
                    if route not in existing.retrieval_routes:
                        existing.retrieval_routes.append(route)
                # Merge sources
                for src in cand.evidence_sources:
                    if src not in existing.evidence_sources:
                        existing.evidence_sources.append(src)
                # Merge target relations
                existing_syms = {tr.target_symbol for tr in existing.target_relations}
                for tr in cand.target_relations:
                    if tr.target_symbol not in existing_syms:
                        existing.target_relations.append(tr)
                        existing.targets_targeted.append(tr.target_symbol)
                # Merge provenance PMIDs
                for pmid in cand.provenance.get("pmids", []):
                    if pmid not in existing.provenance.get("pmids", []):
                        existing.provenance.setdefault("pmids", []).append(pmid)
                # Keep best bioactivity
                if cand.best_bioactivity_nM is not None:
                    if (
                        existing.best_bioactivity_nM is None
                        or cand.best_bioactivity_nM < existing.best_bioactivity_nM
                    ):
                        existing.best_bioactivity_nM = cand.best_bioactivity_nM
                # Accumulate citation count
                existing.citation_count += cand.citation_count

        # Sort: dual-route first, then by citation count, then alphabetically
        def _sort_key(c: CompoundCandidate) -> Tuple:
            is_dual = (
                "disease_natural_literature" in c.retrieval_routes
                and "protein_chembl_bioactivity" in c.retrieval_routes
            )
            has_bioactivity = c.best_bioactivity_nM is not None
            return (
                0 if is_dual else 1,
                0 if has_bioactivity else 1,
                -(c.citation_count),
                c.name,
            )

        return sorted(merged.values(), key=_sort_key)
