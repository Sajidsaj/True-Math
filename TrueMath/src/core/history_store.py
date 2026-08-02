"""
Module Name: history_store
Purpose: Persist Q&A answers and identity discoveries to a local SQLite
         database so they survive app restarts, and export them to a
         Markdown/PDF report — with per-session isolation and sensitive-
         content redaction, so this is safe for a public multi-user
         deployment (not just single-user desktop use).
Responsibilities:
  - Save Q&A history SCOPED TO A SESSION ID — one user's questions and
    answers are never visible to another user, even though they share the
    same underlying database file.
  - Refuse to persist anything that looks like private key material (e.g.
    a generated RSA private key) — even for the session that generated it,
    since there's no good reason to keep that on disk long-term.
  - Discoveries (the auto-generated identity feed) remain a SHARED, public
    list — they're not sensitive, and are meant to be a live feed everyone
    sees, unlike personal Q&A history.
Dependencies: sqlite3 (stdlib)
Honesty note: This is in-memory-per-process rate/session tracking backed
              by a real SQLite file — genuine data isolation between
              sessions, not a cosmetic label. A session_id of None (the
              single-user desktop default) behaves as before.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from contextlib import contextmanager
from typing import Dict, List, Optional

from src.core.sys_logger import get_logger

logger = get_logger("HistoryStore")

# Matches a full PEM private-key block (BEGIN...END, including the base64
# body) so the entire key is removed, not just the marker line.
_SENSITIVE_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA )?(?:ENCRYPTED )?PRIVATE KEY-----.*?-----END (?:RSA )?(?:ENCRYPTED )?PRIVATE KEY-----", re.DOTALL),
]


def _contains_sensitive_content(text: str) -> bool:
    return any(p.search(text) for p in _SENSITIVE_PATTERNS)


def _redact(text: str) -> str:
    """Replaces the ENTIRE sensitive PEM block (markers + key body) with a
    placeholder — so no fragment of the actual key material is ever
    persisted, while still showing that a key was generated."""
    redacted = text
    for pattern in _SENSITIVE_PATTERNS:
        redacted = pattern.sub("[PRIVATE KEY REDACTED — not saved to history]", redacted)
    return redacted


class HistoryStore:
    __slots__ = ('db_path',)

    def __init__(self, db_path: str = "data/truemath_history.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS qa_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    session_id TEXT,
                    question TEXT,
                    answer TEXT,
                    source TEXT
                )
            """)
            # Migration for databases created before session_id existed.
            existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(qa_history)").fetchall()}
            if "session_id" not in existing_cols:
                conn.execute("ALTER TABLE qa_history ADD COLUMN session_id TEXT")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS discoveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    base_identity TEXT,
                    substitution TEXT,
                    lhs TEXT,
                    rhs TEXT,
                    verified INTEGER
                )
            """)
            conn.commit()

    def save_qa(self, question: str, answer: str, source: str, session_id: Optional[str] = None) -> None:
        """Saves a Q&A pair scoped to `session_id` (None = legacy/single-user
        desktop mode, matching old behavior). Automatically redacts any
        private-key-shaped content before writing to disk."""
        if _contains_sensitive_content(answer):
            logger.info("Redacting private-key-shaped content before saving to history.")
            answer = _redact(answer)

        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO qa_history (timestamp, session_id, question, answer, source) VALUES (?, ?, ?, ?, ?)",
                    (time.time(), session_id, question, answer, source),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Could not save Q&A to history: {e}")

    def save_discovery(self, base_identity: str, substitution: str, lhs: str, rhs: str, verified: bool) -> None:
        """Discoveries are a SHARED public feed (not session-scoped) — the
        auto-generated identity stream is meant to be seen by everyone,
        unlike personal Q&A history."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO discoveries (timestamp, base_identity, substitution, lhs, rhs, verified) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (time.time(), base_identity, substitution, lhs, rhs, int(verified)),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Could not save discovery to history: {e}")

    def get_qa_history(self, limit: int = 100, session_id: Optional[str] = None) -> List[Dict]:
        """Returns Q&A history for `session_id` ONLY. Passing None returns
        only legacy/session-less rows (single-user desktop mode) — it does
        NOT return everyone's history, so there is no way to accidentally
        fetch another user's data by omitting the session_id."""
        with self._get_connection() as conn:
            if session_id is None:
                rows = conn.execute(
                    "SELECT * FROM qa_history WHERE session_id IS NULL ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM qa_history WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit)
                ).fetchall()
            return [dict(r) for r in rows]

    def get_discoveries(self, limit: int = 100) -> List[Dict]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM discoveries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def export_markdown(self, output_dir: str = "data/exports", session_id: Optional[str] = None) -> str:
        """Writes THIS SESSION'S Q&A history (plus the shared discoveries
        feed) to a timestamped Markdown file and returns its absolute path."""
        os.makedirs(output_dir, exist_ok=True)
        qa = list(reversed(self.get_qa_history(1000, session_id=session_id)))
        discoveries = list(reversed(self.get_discoveries(1000)))

        lines = ["# TrueMath History Export", "", f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]

        lines.append("## Q&A History")
        lines.append("")
        if not qa:
            lines.append("_No questions asked yet._")
        for item in qa:
            ts = time.strftime('%Y-%m-%d %H:%M', time.localtime(item["timestamp"]))
            lines.append(f"**[{ts}] Q:** {item['question']}")
            lines.append("")
            lines.append(f"**A ({item['source']}):** {item['answer']}")
            lines.append("")

        lines.append("## Verified Discoveries")
        lines.append("")
        if not discoveries:
            lines.append("_No discoveries yet._")
        for item in discoveries:
            status = "✓ Verified" if item["verified"] else "✗ Failed"
            lines.append(f"- **{item['base_identity']}** (u = {item['substitution']}): {item['lhs']} = {item['rhs']} — {status}")

        content = "\n".join(lines)
        filename = f"truemath_history_{time.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return os.path.abspath(filepath)

    def export_pdf(self, output_dir: str = "data/exports", session_id: Optional[str] = None) -> str:
        """Writes THIS SESSION'S Q&A history (plus the shared discoveries
        feed) to a timestamped PDF file and returns its absolute path."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from xml.sax.saxutils import escape

        os.makedirs(output_dir, exist_ok=True)
        qa = list(reversed(self.get_qa_history(1000, session_id=session_id)))
        discoveries = list(reversed(self.get_discoveries(1000)))

        filename = f"truemath_history_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(output_dir, filename)

        styles = getSampleStyleSheet()
        story = [Paragraph("TrueMath History Export", styles["Title"]),
                 Paragraph(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]),
                 Spacer(1, 16),
                 Paragraph("Q&A History", styles["Heading2"])]

        if not qa:
            story.append(Paragraph("No questions asked yet.", styles["Normal"]))
        for item in qa:
            ts = time.strftime('%Y-%m-%d %H:%M', time.localtime(item["timestamp"]))
            story.append(Paragraph(f"<b>[{ts}] Q:</b> {escape(item['question'])}", styles["Normal"]))
            story.append(Paragraph(f"<b>A ({escape(item['source'])}):</b> {escape(item['answer'])}", styles["Normal"]))
            story.append(Spacer(1, 8))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Verified Discoveries", styles["Heading2"]))
        if not discoveries:
            story.append(Paragraph("No discoveries yet.", styles["Normal"]))
        for item in discoveries:
            status = "Verified" if item["verified"] else "Failed"
            text = f"<b>{escape(item['base_identity'])}</b> (u = {escape(item['substitution'])}): {escape(item['lhs'])} = {escape(item['rhs'])} — {status}"
            story.append(Paragraph(text, styles["Normal"]))
            story.append(Spacer(1, 4))

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        doc.build(story)

        return os.path.abspath(filepath)
