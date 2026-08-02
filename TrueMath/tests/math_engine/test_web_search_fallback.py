from src.math_engine.web_search_fallback import search_web


def test_empty_query_rejected():
    result = search_web("")
    assert result["status"] == "error"


def test_search_never_crashes_on_network_issues():
    # Even if the network call fails entirely, this must return a clean
    # status dict, never raise an exception up to the caller.
    result = search_web("some query that might fail in a sandboxed test env")
    assert result["status"] in ("ok", "error")
    assert "message" in result
