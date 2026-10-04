from literature_retriever.query_builder import (
    LiteratureQueryBuilder
)


def test_disease_target_query():

    query = LiteratureQueryBuilder.disease_target_query(
        "type 2 diabetes mellitus",
        "KCNJ11"
    )

    assert query == (
        '"type 2 diabetes mellitus" AND KCNJ11'
    )


def test_query_strips_whitespace():

    query = LiteratureQueryBuilder.disease_target_query(
        "  type 2 diabetes mellitus  ",
        "  KCNJ11  "
    )

    assert query == (
        '"type 2 diabetes mellitus" AND KCNJ11'
    )


def test_empty_disease():

    try:
        LiteratureQueryBuilder.disease_target_query(
            "",
            "KCNJ11"
        )
        assert False

    except ValueError as exc:
        assert str(exc) == "Disease name cannot be empty"


def test_empty_target():

    try:
        LiteratureQueryBuilder.disease_target_query(
            "type 2 diabetes mellitus",
            ""
        )
        assert False

    except ValueError as exc:
        assert str(exc) == "Target symbol cannot be empty"


def test_whitespace_disease():

    try:
        LiteratureQueryBuilder.disease_target_query(
            "   ",
            "KCNJ11"
        )
        assert False

    except ValueError as exc:
        assert str(exc) == "Disease name cannot be empty"


def test_whitespace_target():

    try:
        LiteratureQueryBuilder.disease_target_query(
            "type 2 diabetes mellitus",
            "   "
        )
        assert False

    except ValueError as exc:
        assert str(exc) == "Target symbol cannot be empty"