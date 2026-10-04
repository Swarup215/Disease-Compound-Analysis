from literature_retriever.models import (
    Paper,
    LiteratureRetrievalResult,
    TargetLiteratureResult,
    BatchLiteratureResult
)

from literature_retriever.pubmed import PubMedClient

from literature_retriever.query_builder import (
    LiteratureQueryBuilder
)


class LiteratureRetriever:

    def __init__(self):
        self.pubmed = PubMedClient()

    def search(
        self,
        query: str,
        top_n: int = 10
    ) -> LiteratureRetrievalResult:

        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if top_n <= 0:
            raise ValueError(
                "top_n must be greater than 0"
            )

        # -------------------------
        # Step 1: Search PubMed
        # -------------------------

        search_result = self.pubmed.search(
            query=query,
            retmax=top_n
        )

        total_found = int(
            search_result.get("count", 0)
        )

        pmids = search_result.get(
            "idlist",
            []
        )

        # -------------------------
        # No papers found
        # -------------------------

        if not pmids:

            return LiteratureRetrievalResult(
                query=query,
                total_found=total_found,
                retrieved_papers=0,
                papers=[]
            )

        # -------------------------
        # Step 2: Fetch papers
        # -------------------------

        xml = self.pubmed.fetch(pmids)

        # -------------------------
        # Step 3: Parse XML
        # -------------------------

        article_data = self.pubmed.parse_articles(
            xml
        )

        # -------------------------
        # Step 4: Convert to Paper
        # -------------------------

        papers = []

        for article in article_data:

            paper = Paper(
                pmid=article["pmid"],
                title=article["title"] or "",
                abstract=article["abstract"],
                journal=article["journal"],
                publication_date=article[
                    "publication_date"
                ],
                doi=article["doi"],
                authors=article["authors"]
            )

            papers.append(paper)

        # -------------------------
        # Step 5: Return result
        # -------------------------

        return LiteratureRetrievalResult(
            query=query,
            total_found=total_found,
            retrieved_papers=len(papers),
            papers=papers
        )

    def search_target(
        self,
        disease_name: str,
        target_symbol: str,
        top_n: int = 10
    ) -> TargetLiteratureResult:

        # -------------------------
        # Step 1: Build query
        # -------------------------

        query = LiteratureQueryBuilder.disease_target_query(
            disease_name=disease_name,
            target_symbol=target_symbol
        )

        # -------------------------
        # Step 2: Search literature
        # -------------------------

        result = self.search(
            query=query,
            top_n=top_n
        )

        return TargetLiteratureResult(
            disease_name=disease_name,
            target_symbol=target_symbol,
            query=result.query,
            total_found=result.total_found,
            retrieved_papers=result.retrieved_papers,
            papers=result.papers
        )

    def search_targets(
        self,
        disease_name: str,
        target_symbols: list[str],
        papers_per_target: int = 5
    ) -> BatchLiteratureResult:

        if not disease_name or not disease_name.strip():
            raise ValueError(
                "Disease name cannot be empty"
            )

        if not target_symbols:
            raise ValueError(
                "Target symbols cannot be empty"
            )

        if papers_per_target <= 0:
            raise ValueError(
                "papers_per_target must be greater than 0"
            )

        target_results = []

        unique_papers = {}

        for target_symbol in target_symbols:

            result = self.search_target(
                disease_name=disease_name,
                target_symbol=target_symbol,
                top_n=papers_per_target
            )

            target_results.append(result)

            for paper in result.papers:

                if paper.pmid not in unique_papers:
                    unique_papers[paper.pmid] = paper

        papers = list(unique_papers.values())

        return BatchLiteratureResult(
            disease_name=disease_name,
            total_targets=len(target_symbols),
            processed_targets=len(target_results),
            total_papers=len(papers),
            papers=papers,
            target_results=target_results
        )