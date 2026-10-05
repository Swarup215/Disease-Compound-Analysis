import logging
from typing import Dict, List, Optional

from literature_retriever.models import (
    Paper,
    LiteratureRetrievalResult,
    TargetLiteratureResult,
    BatchLiteratureResult
)
from literature_retriever.pubmed import PubMedClient
from literature_retriever.europe_pmc import EuropePMCClient
from literature_retriever.open_targets_literature import OpenTargetsLiteratureClient
from literature_retriever.query_builder import LiteratureQueryBuilder

logger = logging.getLogger(__name__)


class LiteratureRetriever:
    """
    Multi-source literature retriever for biomedical targets and diseases.
    Harvests scientific papers and abstracts across:
    1. NCBI PubMed (Entrez E-Utilities API)
    2. Europe PMC (EMBL-EBI REST API — covers PubMed, PubMed Central open access, and preprints)
    3. Open Targets Platform (Curated and text-mined disease-target literature evidence)
    """

    def __init__(self):
        self.pubmed = PubMedClient()
        self.europe_pmc = EuropePMCClient()
        self.open_targets_lit = OpenTargetsLiteratureClient()

    def search(
        self,
        query: str,
        top_n: int = 10,
        include_europe_pmc: bool = True
    ) -> LiteratureRetrievalResult:
        """
        Searches literature across PubMed and Europe PMC for the given query.
        Results are deduplicated by PMID, DOI, and title.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if top_n <= 0:
            raise ValueError("top_n must be greater than 0")

        total_found = 0
        papers: List[Paper] = []
        seen_pmids: set[str] = set()
        active_sources: List[str] = []

        # -------------------------------------------------------------
        # Step 1: Search NCBI PubMed
        # -------------------------------------------------------------
        try:
            search_result = self.pubmed.search(query=query, retmax=top_n)
            total_found += int(search_result.get("count", 0))
            pmids = search_result.get("idlist", [])

            if pmids:
                active_sources.append("PubMed")
                xml = self.pubmed.fetch(pmids)
                article_data = self.pubmed.parse_articles(xml)

                for article in article_data:
                    pmid_str = str(article["pmid"]).strip()
                    paper = Paper(
                        pmid=pmid_str,
                        title=article["title"] or "",
                        abstract=article["abstract"],
                        journal=article["journal"],
                        publication_date=article["publication_date"],
                        doi=article["doi"],
                        authors=article["authors"],
                        source="PubMed",
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid_str}/",
                        pmcid=None
                    )
                    papers.append(paper)
                    seen_pmids.add(pmid_str)
        except Exception as exc:
            logger.warning(f"PubMed search failed for query '{query}': {exc}")

        # -------------------------------------------------------------
        # Step 2: Search EMBL-EBI Europe PMC
        # -------------------------------------------------------------
        if include_europe_pmc:
            try:
                epmc_items = self.europe_pmc.search(query=query, page_size=top_n)
                if epmc_items:
                    if "Europe PMC" not in active_sources:
                        active_sources.append("Europe PMC")
                    epmc_articles = self.europe_pmc.parse_articles(epmc_items)

                    for art in epmc_articles:
                        pmid_str = str(art["pmid"]).strip()

                        # Deduplication: If already retrieved via PubMed, enrich metadata
                        if pmid_str in seen_pmids:
                            for existing in papers:
                                if existing.pmid == pmid_str:
                                    if "Europe PMC" not in existing.source:
                                        existing.source = f"{existing.source}, Europe PMC"
                                    if not existing.abstract and art.get("abstract"):
                                        existing.abstract = art["abstract"]
                                    if not existing.doi and art.get("doi"):
                                        existing.doi = art["doi"]
                                    if not existing.pmcid and art.get("pmcid"):
                                        existing.pmcid = art["pmcid"]
                                    break
                        else:
                            # New unique paper from Europe PMC (e.g. PMC full-text or Preprint)
                            paper = Paper(
                                pmid=pmid_str,
                                title=art["title"] or "",
                                abstract=art["abstract"],
                                journal=art["journal"],
                                publication_date=art["publication_date"],
                                doi=art["doi"],
                                authors=art["authors"],
                                source=art["source"],
                                url=art["url"],
                                pmcid=art["pmcid"]
                            )
                            papers.append(paper)
                            seen_pmids.add(pmid_str)
            except Exception as exc:
                logger.warning(f"Europe PMC search failed for query '{query}': {exc}")

        # Limit to top_n results while ensuring quality
        trimmed_papers = papers[:top_n]

        return LiteratureRetrievalResult(
            query=query,
            total_found=max(total_found, len(papers)),
            retrieved_papers=len(trimmed_papers),
            sources=active_sources,
            papers=trimmed_papers
        )

    def search_target(
        self,
        disease_name: str,
        target_symbol: str,
        top_n: int = 10,
        disease_id: Optional[str] = None,
        target_ensembl_id: Optional[str] = None
    ) -> TargetLiteratureResult:
        """
        Searches literature for a specific disease and target combination across
        PubMed, Europe PMC, and Open Targets literature mining evidence.
        """
        # Step 1: Build boolean search query
        query = LiteratureQueryBuilder.disease_target_query(
            disease_name=disease_name,
            target_symbol=target_symbol
        )

        # Step 2: Search primary literature sources (PubMed + Europe PMC)
        result = self.search(
            query=query,
            top_n=top_n,
            include_europe_pmc=True
        )

        papers = list(result.papers)
        sources = list(result.sources)
        seen_pmids = {p.pmid for p in papers}

        # Step 3: Complement with Open Targets verified literature evidence if available
        if disease_id and target_ensembl_id:
            try:
                ot_evidences = self.open_targets_lit.get_evidence_pmids(
                    disease_id=disease_id,
                    target_ensembl_id=target_ensembl_id,
                    size=top_n
                )

                if ot_evidences:
                    if "Open Targets" not in sources:
                        sources.append("Open Targets")

                    # Check which PMIDs are not yet retrieved
                    missing_pmids = [
                        item["pmid"] for item in ot_evidences
                        if item["pmid"] not in seen_pmids
                    ]

                    # Also mark existing papers as verified by Open Targets
                    ot_pmid_set = {item["pmid"] for item in ot_evidences}
                    for p in papers:
                        if p.pmid in ot_pmid_set and "Open Targets" not in p.source:
                            p.source = f"{p.source} + Open Targets"

                    # If we need more papers to reach top_n, fetch the missing Open Targets PMIDs
                    if missing_pmids and len(papers) < top_n:
                        needed_count = top_n - len(papers)
                        to_fetch = missing_pmids[:needed_count]
                        try:
                            xml = self.pubmed.fetch(to_fetch)
                            ot_articles = self.pubmed.parse_articles(xml)
                            for article in ot_articles:
                                pmid_str = str(article["pmid"]).strip()
                                paper = Paper(
                                    pmid=pmid_str,
                                    title=article["title"] or "",
                                    abstract=article["abstract"],
                                    journal=article["journal"],
                                    publication_date=article["publication_date"],
                                    doi=article["doi"],
                                    authors=article["authors"],
                                    source="Open Targets / PubMed",
                                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid_str}/",
                                    pmcid=None
                                )
                                papers.append(paper)
                                seen_pmids.add(pmid_str)
                        except Exception as fetch_exc:
                            logger.warning(f"Failed to fetch missing Open Targets PMIDs {to_fetch}: {fetch_exc}")
            except Exception as ot_exc:
                logger.warning(f"Failed to query Open Targets literature evidence for {target_symbol}: {ot_exc}")

        return TargetLiteratureResult(
            disease_name=disease_name,
            target_symbol=target_symbol,
            query=result.query,
            total_found=max(result.total_found, len(papers)),
            retrieved_papers=len(papers),
            sources=sources,
            papers=papers
        )

    def search_targets(
        self,
        disease_name: str,
        target_symbols: List[str],
        papers_per_target: int = 5,
        disease_id: Optional[str] = None,
        target_id_map: Optional[Dict[str, str]] = None
    ) -> BatchLiteratureResult:
        """
        Batch searches literature for multiple candidate targets across
        PubMed, Europe PMC, and Open Targets.
        Deduplicates papers across targets while associating each paper with all relevant targets.
        """
        if not disease_name or not disease_name.strip():
            raise ValueError("Disease name cannot be empty")

        if not target_symbols:
            raise ValueError("Target symbols cannot be empty")

        if papers_per_target <= 0:
            raise ValueError("papers_per_target must be greater than 0")

        target_results = []
        unique_papers: Dict[str, Paper] = {}
        all_sources: set[str] = set()

        for target_symbol in target_symbols:
            target_ensembl_id = target_id_map.get(target_symbol) if target_id_map else None

            result = self.search_target(
                disease_name=disease_name,
                target_symbol=target_symbol,
                top_n=papers_per_target,
                disease_id=disease_id,
                target_ensembl_id=target_ensembl_id
            )

            target_results.append(result)
            all_sources.update(result.sources)

            for paper in result.papers:
                if paper.pmid not in unique_papers:
                    paper.target_symbols = [target_symbol]
                    unique_papers[paper.pmid] = paper
                else:
                    existing_paper = unique_papers[paper.pmid]
                    if target_symbol not in existing_paper.target_symbols:
                        existing_paper.target_symbols.append(target_symbol)
                    # Merge source badges if new source found
                    if paper.source and paper.source not in existing_paper.source:
                        existing_paper.source = f"{existing_paper.source}, {paper.source}"
                    if not existing_paper.abstract and paper.abstract:
                        existing_paper.abstract = paper.abstract
                    if not existing_paper.url and paper.url:
                        existing_paper.url = paper.url
                    if not existing_paper.pmcid and paper.pmcid:
                        existing_paper.pmcid = paper.pmcid

        papers = list(unique_papers.values())

        return BatchLiteratureResult(
            disease_name=disease_name,
            total_targets=len(target_symbols),
            processed_targets=len(target_results),
            total_papers=len(papers),
            sources=sorted(list(all_sources)),
            papers=papers,
            target_results=target_results
        )