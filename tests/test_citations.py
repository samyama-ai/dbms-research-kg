from etl.citations import clean_doi, paper_identity, parse_citation


def test_doi_keeps_balanced_parentheses():
    citation = (
        "**[Foundational]** Fagin, Lotem, Naor. "
        "*Optimal Aggregation Algorithms for Middleware.* "
        "[DOI](https://doi.org/10.1016/S0022-0000(03)00026-6)."
    )
    parsed = parse_citation(citation)
    assert parsed["doi"] == "10.1016/S0022-0000(03)00026-6"


def test_clean_doi_removes_surrounding_punctuation():
    assert clean_doi("10.1234/example(2).") == "10.1234/example(2)"
    assert clean_doi("10.1234/example)") == "10.1234/example"


def test_doi_has_identity_priority():
    parsed = {
        "doi": "10.1234/EXAMPLE.",
        "arxiv_id": "1709.08359",
        "title": "Example",
        "year": 2024,
    }
    assert paper_identity(parsed) == "doi:10.1234/example"


def test_arxiv_identity_ignores_version_suffix():
    first = {"arxiv_id": "cs/0204046v1"}
    second = {"arxiv_id": "cs/0204046v3"}
    assert paper_identity(first) == paper_identity(second) == "arxiv:cs/0204046"


def test_distinct_dois_remain_distinct_with_same_arxiv_id():
    first = {"doi": "10.1145/1111", "arxiv_id": "1709.08359"}
    second = {"doi": "10.4230/2222", "arxiv_id": "1709.08359"}
    assert paper_identity(first) != paper_identity(second)


def test_dblp_fallback():
    assert paper_identity({"dblp_key": "conf/ICDT/Example.html"}) == (
        "dblp:conf/icdt/example"
    )


def test_title_year_fallback():
    parsed = {"title": "An *Example* Paper", "year": 2025}
    assert paper_identity(parsed) == "title:an example paper|year:2025"
