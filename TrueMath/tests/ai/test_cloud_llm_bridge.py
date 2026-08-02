from unittest.mock import patch

from src.ai.cloud_llm_bridge import CloudLLMBridge, _answer_signature


def test_no_keys_configured_reports_clearly():
    bridge = CloudLLMBridge("", "", "", "", "", "", timeout_s=5)
    assert "Koi bhi API key set nahi hai" in bridge.last_error_message()


def test_prompt_ai_tries_groq_then_openrouter():
    bridge = CloudLLMBridge("groq-key", "model", "http://groq", "or-key", "model2", "http://or", timeout_s=5)
    calls = []

    def fake_call(system_prompt, user_prompt, timeout_s):
        calls.append(system_prompt)
        return None  # simulate failure so it falls through to next provider

    with patch.object(bridge._providers[0], "call", side_effect=fake_call), \
         patch.object(bridge._providers[1], "call", return_value="openrouter answer"):
        result = bridge.prompt_ai("sys", "question")
    assert result == "openrouter answer"
    assert len(calls) == 1  # groq was tried first


def test_self_consistency_majority_vote():
    bridge = CloudLLMBridge("fake-key", "model", "http://fake", "", "", "", timeout_s=5)
    responses = iter(["The answer is 4", "It equals 4", "5 is the answer"])
    with patch.object(bridge, "prompt_ai", side_effect=lambda *a, **k: next(responses)):
        answer, agreement, all_answers = bridge.prompt_ai_self_consistent("sys", "what is 2+2", n=3)
    assert "4" in answer
    assert agreement == 2 / 3
    assert len(all_answers) == 3


def test_answer_signature_groups_by_number():
    assert _answer_signature("The answer is 4") == _answer_signature("It equals 4")
    assert _answer_signature("The answer is 4") != _answer_signature("It is 5")


def test_prompt_with_user_key_rejects_unknown_provider():
    bridge = CloudLLMBridge("", "", "", "", "", "", timeout_s=5)
    answer, error = bridge.prompt_with_user_key("sys", "question", "not_a_real_provider", "some-key")
    assert answer is None
    assert error == "invalid_key"


def test_prompt_with_user_key_rejects_empty_key():
    bridge = CloudLLMBridge("", "", "", "", "", "", timeout_s=5)
    answer, error = bridge.prompt_with_user_key("sys", "question", "groq", "")
    assert answer is None
    assert error == "invalid_key"


def test_prompt_with_user_key_uses_caller_key_not_server_key():
    # Server has NO configured keys, but a user-supplied key should still
    # be attempted independently (this is the whole point of the feature).
    bridge = CloudLLMBridge("", "", "", "", "", "", timeout_s=5)
    with patch("src.ai.cloud_llm_bridge._Provider.call", return_value="answer via user key"):
        answer, error = bridge.prompt_with_user_key("sys", "question", "groq", "users-own-key")
    assert answer == "answer via user key"
    assert error is None
