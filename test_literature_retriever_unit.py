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