import html
import logging
import re
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

EUROPE_PMC_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _clean_text(text: Optional[str]) -> str:
    """Removes HTML tags and unescapes HTML entities."""
    if not text:
        return ""
    text = html.unescape(text)
    # Remove HTML tags (e.g. <i>, <b>, <sup>)
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple whitespaces
    return " ".join(text.split())


class EuropePMCClient:
    """
    Client for Europe PMC REST API (EMBL-EBI).
    Searches life sciences literature including PubMed (MEDLINE), PubMed Central (PMC),
    and preprints (bioRxiv, medRxiv, Research Square, etc.).
    """

    def __init__(self, timeout: int = 25):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BiomedicalAI-LiteratureRetriever/1.0 (https://github.com/biomedical-ai; contact: info@biomedical.ai)"
        })
        self.timeout = timeout

    def search(
        self,
        query: str,
        page_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Searches Europe PMC for matching articles.
        Returns a list of raw article dictionary records.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if page_size <= 0:
            raise ValueError("page_size must be greater than 0")

        params = {
            "query": query.strip(),
            "format": "json",
            "pageSize": page_size,
            "resultType": "core"
        }

        try:
            response = self.session.get(
                EUROPE_PMC_BASE_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get("resultList", {}).get("result", [])
        except Exception as exc:
            logger.warning(f"Europe PMC search request failed for query '{query}': {exc}")
            return []

    def parse_articles(
        self,
        raw_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parses raw Europe PMC JSON items into standardized article dictionaries.
        """
        articles = []

        for item in raw_items:
            # Identifier: prefer numeric PMID, otherwise PMCID or EPMC ID
            pmid = item.get("pmid")
            pmcid = item.get("pmcid")
            raw_id = item.get("id")
            source_code = item.get("source", "MED")

            article_id = pmid or pmcid or raw_id
            if not article_id:
                continue

            # Determine human-readable source label
            if source_code == "MED":
                source_label = "Europe PMC (MEDLINE)"
            elif source_code == "PMC":
                source_label = "Europe PMC (PMC)"
            elif source_code == "PPR":
                source_label = "Europe PMC (Preprint)"
            else:
                source_label = f"Europe PMC ({source_code})"

            # Direct web URL
            if pmid:
                web_url = f"https://europepmc.org/article/MED/{pmid}"
            elif pmcid:
                web_url = f"https://europepmc.org/article/PMC/{pmcid}"
            else:
                web_url = f"https://europepmc.org/article/{source_code}/{raw_id}"

            # Extract authors
            authors = []
            author_list = item.get("authorList", {}).get("author", [])
            if isinstance(author_list, list):
                for a in author_list:
                    if isinstance(a, dict) and "fullName" in a:
                        authors.append(a["fullName"])
            if not authors and item.get("authorString"):
                authors = [a.strip() for a in item["authorString"].split(",") if a.strip()]

            # Journal name
            journal_info = item.get("journalInfo")
            journal = None
            if isinstance(journal_info, dict):
                journal_dict = journal_info.get("journal")
                if isinstance(journal_dict, dict):
                    journal = journal_dict.get("title")

            # Publication date
            pub_year = item.get("pubYear")
            pub_date = str(pub_year) if pub_year else item.get("firstPublicationDate")

            title = _clean_text(item.get("title", ""))
            abstract = _clean_text(item.get("abstractText", ""))

            articles.append({
                "pmid": str(article_id),
                "title": title,
                "abstract": abstract if abstract else None,
                "journal": journal,
                "publication_date": pub_date,
                "doi": item.get("doi"),
                "authors": authors,
                "source": source_label,
                "url": web_url,
                "pmcid": pmcid
            })

        return articles
