from src.extract import SEARCH_QUERIES


def test_search_queries_defined():
    assert "data engineer" in SEARCH_QUERIES
    assert "data scientist" in SEARCH_QUERIES
    assert "data analyst" in SEARCH_QUERIES
    assert "machine learning engineer" in SEARCH_QUERIES
