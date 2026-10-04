import requests
import xml.etree.ElementTree as ET


PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedClient:

    def __init__(self):
        self.session = requests.Session()

    def search(
        self,
        query: str,
        retmax: int = 20
    ) -> dict:

        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if retmax <= 0:
            raise ValueError("retmax must be greater than 0")

        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": retmax
        }

        response = self.session.get(
            f"{PUBMED_BASE_URL}/esearch.fcgi",
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        if "esearchresult" not in data:
            raise RuntimeError(
                "Unexpected response from PubMed"
            )

        return data["esearchresult"]

    def fetch(
        self,
        pmids: list[str]
    ) -> str:

        if not pmids:
            raise ValueError("PMID list cannot be empty")

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }

        response = self.session.get(
            f"{PUBMED_BASE_URL}/efetch.fcgi",
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.text
    def parse_articles(
        self,
        xml_text: str
    ) -> list[dict]:

        if not xml_text or not xml_text.strip():
            raise ValueError("XML response cannot be empty")

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ValueError(
                "Invalid PubMed XML"
            ) from exc

        articles = []

        for article in root.findall("PubmedArticle"):

            medline = article.find("MedlineCitation")

            if medline is None:
                continue

            pmid_element = medline.find("PMID")

            if pmid_element is None:
                continue

            pmid = pmid_element.text

            article_data = {
                "pmid": pmid,
                "title": None,
                "abstract": None,
                "journal": None,
                "publication_date": None,
                "doi": None,
                "authors": []
            }

            article_node = medline.find("Article")

            if article_node is None:
                articles.append(article_data)
                continue

            # -------------------------
            # Title
            # -------------------------

            title_element = article_node.find("ArticleTitle")

            if title_element is not None:
                article_data["title"] = "".join(
                    title_element.itertext()
                )

            # -------------------------
            # Abstract
            # -------------------------

            abstract_elements = article_node.findall(
                "Abstract/AbstractText"
            )

            if abstract_elements:

                abstract_parts = []

                for abstract_element in abstract_elements:

                    text = "".join(
                        abstract_element.itertext()
                    )

                    if text:
                        abstract_parts.append(text)

                article_data["abstract"] = " ".join(
                    abstract_parts
                )

            # -------------------------
            # Journal
            # -------------------------

            journal_element = article_node.find(
                "Journal/Title"
            )

            if journal_element is not None:
                article_data["journal"] = journal_element.text

            # -------------------------
            # Publication date
            # -------------------------

            pub_date = article_node.find(
                "Journal/JournalIssue/PubDate"
            )

            if pub_date is not None:

                year = pub_date.findtext("Year")
                month = pub_date.findtext("Month")
                day = pub_date.findtext("Day")

                date_parts = [
                    part
                    for part in [year, month, day]
                    if part
                ]

                article_data["publication_date"] = "-".join(
                    date_parts
                )

            # -------------------------
            # DOI
            # -------------------------

            article_ids = article.findall(
                "PubmedData/ArticleIdList/ArticleId"
            )

            for article_id in article_ids:

                if article_id.get("IdType") == "doi":

                    article_data["doi"] = article_id.text
                    break

            # -------------------------
            # Authors
            # -------------------------

            author_elements = article_node.findall(
                "AuthorList/Author"
            )

            for author in author_elements:

                last_name = author.findtext("LastName")
                initials = author.findtext("Initials")

                if last_name and initials:
                    article_data["authors"].append(
                        f"{last_name} {initials}"
                    )

                elif last_name:
                    article_data["authors"].append(
                        last_name
                    )

            articles.append(article_data)

        return articles