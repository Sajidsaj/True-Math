from src.ai.agent_tools import TOOLS, execute_tool_call


def test_all_tools_have_valid_openai_schema():
    for tool in TOOLS:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert "name" in fn and "description" in fn and "parameters" in fn
        assert fn["parameters"]["type"] == "object"


def test_matrix_determinant_tool_executes_real_computation():
    result = execute_tool_call("matrix_determinant", {"matrix": [[2, 1], [1, 3]]})
    assert result["status"] == "ok"
    assert result["result"]["determinant"] == "5"


def test_gcd_tool_executes_real_computation():
    result = execute_tool_call("number_theory_gcd", {"a": 48, "b": 18})
    assert result["status"] == "ok"
    assert result["result"] == 6


def test_explore_number_tool_executes_real_computation():
    result = execute_tool_call("explore_number", {"n": 8128})
    assert result["status"] == "ok"
    assert result["result"]["is_perfect_number"] is True


def test_unknown_tool_handled_gracefully():
    result = execute_tool_call("not_a_real_tool", {})
    assert result["status"] == "error"


def test_bad_arguments_handled_gracefully():
    result = execute_tool_call("matrix_determinant", {"wrong_key": "oops"})
    assert result["status"] == "error"
