import os
import tempfile

import pytest

from src.core.history_store import HistoryStore


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test_history.db")
    return HistoryStore(db_path=db_path)


def test_save_and_retrieve_qa(store):
    store.save_qa("2+2", "4", "computed")
    history = store.get_qa_history()
    assert len(history) == 1
    assert history[0]["question"] == "2+2"
    assert history[0]["answer"] == "4"


def test_save_and_retrieve_discovery(store):
    store.save_discovery("Pythagorean identity", "x", "sin(x)**2+cos(x)**2", "1", True)
    discoveries = store.get_discoveries()
    assert len(discoveries) == 1
    assert discoveries[0]["verified"] == 1


def test_history_persists_across_instances(tmp_path):
    db_path = str(tmp_path / "persist.db")
    store1 = HistoryStore(db_path=db_path)
    store1.save_qa("question 1", "answer 1", "computed")

    # A brand new HistoryStore instance pointed at the same file must see it
    store2 = HistoryStore(db_path=db_path)
    history = store2.get_qa_history()
    assert len(history) == 1
    assert history[0]["question"] == "question 1"


def test_export_markdown(store, tmp_path):
    store.save_qa("2+2", "4", "computed")
    export_dir = str(tmp_path / "exports")
    path = store.export_markdown(output_dir=export_dir)
    assert os.path.exists(path)
    content = open(path, encoding="utf-8").read()
    assert "2+2" in content
    assert "4" in content


def test_export_pdf(store, tmp_path):
    store.save_qa("2+2", "4", "computed")
    export_dir = str(tmp_path / "exports")
    path = store.export_pdf(output_dir=export_dir)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


def test_session_isolation_users_cannot_see_each_others_history(store):
    store.save_qa("user A question", "answer A", "computed", session_id="session_A")
    store.save_qa("user B question", "answer B", "computed", session_id="session_B")

    history_a = store.get_qa_history(session_id="session_A")
    history_b = store.get_qa_history(session_id="session_B")

    assert len(history_a) == 1
    assert history_a[0]["question"] == "user A question"
    assert len(history_b) == 1
    assert history_b[0]["question"] == "user B question"
    # Critical: neither session's export/history call should ever surface
    # the other session's data.
    assert "user B question" not in [h["question"] for h in history_a]
    assert "user A question" not in [h["question"] for h in history_b]


def test_none_session_id_does_not_leak_other_sessions_data(store):
    store.save_qa("scoped question", "scoped answer", "computed", session_id="session_A")
    store.save_qa("legacy question", "legacy answer", "computed", session_id=None)

    legacy_history = store.get_qa_history(session_id=None)
    assert len(legacy_history) == 1
    assert legacy_history[0]["question"] == "legacy question"


def test_private_key_never_persisted_to_history(store):
    answer_with_key = (
        "Here is your key:\n"
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwSECRETDATAHERE\n"
        "-----END PRIVATE KEY-----\n"
        "Keep it safe."
    )
    store.save_qa("generate rsa key", answer_with_key, "router", session_id="session_A")
    history = store.get_qa_history(session_id="session_A")
    assert "SECRETDATAHERE" not in history[0]["answer"]
    assert "BEGIN PRIVATE KEY" not in history[0]["answer"]
    assert "REDACTED" in history[0]["answer"]
    # The fact that a key was generated is still visible, just not the key itself
    assert "Keep it safe." in history[0]["answer"]


def test_export_only_includes_callers_own_session(store, tmp_path):
    store.save_qa("session A secret question", "answer A", "computed", session_id="session_A")
    store.save_qa("session B secret question", "answer B", "computed", session_id="session_B")

    export_dir = str(tmp_path / "exports")
    path = store.export_markdown(output_dir=export_dir, session_id="session_A")
    content = open(path, encoding="utf-8").read()

    assert "session A secret question" in content
    assert "session B secret question" not in content
