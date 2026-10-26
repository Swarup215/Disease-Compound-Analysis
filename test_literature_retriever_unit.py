from literature_retriever.models import (
    Paper,
    LiteratureRetrievalResult
)

from literature_retriever.retriever import (
    LiteratureRetriever
)


def test_paper_model():

    paper = Paper(
        pmid="123456",
        title="Test paper",
        abstract="This is a test abstract.",
        journal="Test Journal",
        publication_date="2026",
        doi="10.1234/test",
        authors=["Smith J", "Doe A"]
    )

    assert paper.pmid == "123456"
    assert paper.title == "Test paper"
    assert paper.abstract == "This is a test abstract."
    assert paper.journal == "Test Journal"
    assert paper.doi == "10.1234/test"
    assert len(paper.authors) == 2


def test_empty_literature_result():

    result = LiteratureRetrievalResult(
        query="test query"
    )

    assert result.query == "test query"
    assert result.total_found == 0
    assert result.retrieved_papers == 0
    assert result.papers == []


def test_retriever_initialization():

    retriever = LiteratureRetriever()

    assert retriever.pubmed is not None


def test_empty_query():

    retriever = LiteratureRetriever()

    try:
        retriever.search(
            query="",
            top_n=5
        )
        assert False

    except ValueError:
        assert True


def test_invalid_top_n():

    retriever = LiteratureRetriever()

    try:
        retriever.search(
            query="KCNJ11",
            top_n=0
        )
        assert False

    except ValueError:
        assert True


def test_paper_creation_from_dictionary():

    article = {
        "pmid": "123456",
        "title": "Example paper",
        "abstract": "Example abstract",
        "journal": "Example Journal",
        "publication_date": "2026",
        "doi": "10.1234/example",
        "authors": ["Smith J"]
    }

    paper = Paper(
        pmid=article["pmid"],
        title=article["title"],
        abstract=article["abstract"],
        journal=article["journal"],
        publication_date=article["publication_date"],
        doi=article["doi"],
        authors=article["authors"]
    )

    assert paper.pmid == "123456"
    assert paper.title == "Example paper"
    assert paper.authors == ["Smith J"]


def test_europe_pmc_client_initialization():
    from literature_retriever.europe_pmc import EuropePMCClient
    client = EuropePMCClient()
    assert client.session is not None
    assert client.timeout > 0


def test_europe_pmc_article_parsing():
    from literature_retriever.europe_pmc import EuropePMCClient
    client = EuropePMCClient()

    sample_items = [
        {
            "id": "33101408",
            "source": "MED",
            "pmid": "33101408",
            "pmcid": "PMC7680000",
            "doi": "10.1000/182",
            "title": "KCNJ11 Mutations in <i>Diabetes</i>",
            "abstractText": "<b>Background</b>: ATP-sensitive K+ channels play a role.",
            "pubYear": "2020",
            "journalInfo": {"journal": {"title": "Journal of Diabetes"}},
            "authorList": {"author": [{"fullName": "Doe John"}, {"fullName": "Smith Jane"}]}
        },
        {
            "id": "PPR12345",
            "source": "PPR",
            "title": "Preprint on Target Regulation",
            "abstractText": "Preprint abstract content.",
            "pubYear": "2026",
            "authorString": "Alpha A, Beta B"
        }
    ]

    parsed = client.parse_articles(sample_items)
    assert len(parsed) == 2
    
    med_article = parsed[0]
    assert med_article["pmid"] == "33101408"
    assert med_article["title"] == "KCNJ11 Mutations in Diabetes"
    assert "ATP-sensitive" in med_article["abstract"]
    assert med_article["journal"] == "Journal of Diabetes"
    assert med_article["source"] == "Europe PMC (MEDLINE)"
    assert len(med_article["authors"]) == 2

    ppr_article = parsed[1]
    assert ppr_article["pmid"] == "PPR12345"
    assert ppr_article["source"] == "Europe PMC (Preprint)"
    assert len(ppr_article["authors"]) == 2


def test_multi_source_retriever_initialization():
    retriever = LiteratureRetriever()
    assert retriever.pubmed is not None
    assert retriever.europe_pmc is not None
    assert retriever.open_targets_lit is not None