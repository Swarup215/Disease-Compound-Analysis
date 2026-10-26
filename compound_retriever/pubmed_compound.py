"""
pubmed_compound.py
------------------
PubMed client for natural compound retrieval.

Route A: Queries PubMed for natural compounds associated with a disease name.
Route B: Queries PubMed for compounds associated with a specific protein target.

Parses article abstracts to extract compound mention snippets that are returned
as evidence alongside the PMID for provenance.
"""

import re
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import requests

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# ---------------------------------------------------------------------------
# Compound-mention extraction patterns
# ---------------------------------------------------------------------------
COMPOUND_MENTION_PATTERNS: List[re.Pattern] = [
    re.compile(
        r"\b(flavonoid|polyphenol|alkaloid|terpenoid|terpene|saponin|"
        r"phenolic|anthocyanin|catechin|quercetin|resveratrol|curcumin|"
        r"berberine|epigallocatechin|rutin|kaempferol|apigenin|luteolin|"
        r"naringenin|hesperidin|naringin|ginsenoside|baicalein|"
        r"ellagic acid|gallic acid|chlorogenic acid|rosmarinic acid|"
        r"ursolic acid|oleanolic acid|betulinic acid|camptothecin|"
        r"paclitaxel|vinblastine|vincristine|colchicine|podophyllotoxin|"
        r"silymarin|silybinin|lignin|coumarin|stilbene|xanthone|"
        r"phytochemical|natural compound|natural product|plant extract|"
        r"herb[a-z]*|botanical|phyto[a-z]+)\b",
        re.IGNORECASE,
    ),
]


def _extract_compound_snippets(abstract: str, max_snippets: int = 5) -> List[str]:
    """Return up to *max_snippets* sentences from *abstract* that mention compounds."""
    sentences = re.split(r"(?<=[.!?])\s+", abstract or "")
    snippets: List[str] = []
    for sent in sentences:
        if any(p.search(sent) for p in COMPOUND_MENTION_PATTERNS):
            snippets.append(sent.strip())
            if len(snippets) >= max_snippets:
                break
    return snippets


class PubMedCompoundClient:
    """Lightweight PubMed client for compound-related queries."""

    _RATE_LIMIT_DELAY = 0.35  # seconds between requests (<=3 req/s without API key)

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        self.api_key = api_key
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._RATE_LIMIT_DELAY:
            time.sleep(self._RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _build_params(self, extra: Dict) -> Dict:
        params = dict(extra)
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_pmids(self, query: str, retmax: int = 20) -> List[str]:
        """Search PubMed and return a list of PMIDs."""
        if not query or not query.strip():
            return []
        self._throttle()
        params = self._build_params({
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": retmax,
        })
        try:
            resp = self.session.get(
                f"{PUBMED_BASE_URL}/esearch.fcgi",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("esearchresult", {}).get("idlist", [])
        except Exception:
            return []

    def fetch_articles(self, pmids: List[str]) -> List[Dict]:
        """Fetch and parse PubMed articles for a list of PMIDs."""
        if not pmids:
            return []
        self._throttle()
        params = self._build_params({
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        })
        try:
            resp = self.session.get(
                f"{PUBMED_BASE_URL}/efetch.fcgi",
                params=params,
                timeout=45,
            )
            resp.raise_for_status()
            return self._parse_xml(resp.text)
        except Exception:
            return []

    def search_and_fetch(self, query: str, retmax: int = 20) -> List[Dict]:
        """Combined search + fetch convenience method."""
        pmids = self.search_pmids(query, retmax=retmax)
        if not pmids:
            return []
        return self.fetch_articles(pmids)

    # ------------------------------------------------------------------
    # XML Parsing
    # ------------------------------------------------------------------

    def _parse_xml(self, xml_text: str) -> List[Dict]:
        """Parse PubMed XML eFetch response into article dicts."""
        if not xml_text or not xml_text.strip():
            return []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        articles = []
        for article_node in root.findall("PubmedArticle"):
            medline = article_node.find("MedlineCitation")
            if medline is None:
                continue
            pmid_el = medline.find("PMID")
            if pmid_el is None:
                continue
            pmid = pmid_el.text or ""

            article_el = medline.find("Article")
            title, abstract, journal, pub_date = "", "", "", ""
            doi: Optional[str] = None
            authors: List[str] = []

            if article_el is not None:
                # Title
                title_el = article_el.find("ArticleTitle")
                if title_el is not None:
                    title = "".join(title_el.itertext())

                # Abstract
                abs_parts = []
                for abs_el in article_el.findall("Abstract/AbstractText"):
                    part = "".join(abs_el.itertext()).strip()
                    if part:
                        abs_parts.append(part)
                abstract = " ".join(abs_parts)

                # Journal
                jrnl_el = article_el.find("Journal/Title")
                if jrnl_el is not None:
                    journal = jrnl_el.text or ""

                # Pub date
                pd = article_el.find("Journal/JournalIssue/PubDate")
                if pd is not None:
                    parts = [
                        pd.findtext("Year") or "",
                        pd.findtext("Month") or "",
                        pd.findtext("Day") or "",
                    ]
                    pub_date = "-".join(p for p in parts if p)

                # Authors
                for au in article_el.findall("AuthorList/Author"):
                    last = au.findtext("LastName") or ""
                    initials = au.findtext("Initials") or ""
                    name = f"{last} {initials}".strip()
                    if name:
                        authors.append(name)

            # DOI
            for aid in article_node.findall("PubmedData/ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = aid.text
                    break

            # Compound evidence snippets extracted from abstract
            snippets = _extract_compound_snippets(abstract)

            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "publication_date": pub_date,
                "doi": doi,
                "authors": authors,
                "compound_snippets": snippets,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })

        return articles
