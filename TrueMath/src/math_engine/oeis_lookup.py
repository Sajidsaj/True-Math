"""
Module Name: oeis_lookup
Purpose: Look up a user-supplied integer sequence against the real OEIS
         (Online Encyclopedia of Integer Sequences, oeis.org) — a genuine
         external database check, not an LLM guess.
Responsibilities:
  - Parse a comma/space-separated list of integers.
  - Query the real OEIS search API.
  - Report matching known sequences (name + OEIS ID), or that no match was
    found (which is common for short/generic sequences and doesn't imply
    anything mathematically interesting).
Dependencies: urllib
Honesty note: "Not found in OEIS" does NOT mean a sequence is novel or
              significant — OEIS only lists sequences someone submitted;
              plenty of ordinary sequences simply were never added. This
              module only reports what the database says, nothing more.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional, TypedDict

import certifi

from src.core.sys_logger import get_logger

logger = get_logger("OEISLookup")

# See arxiv_search.py for why this is needed — some Windows Python installs
# have a missing/misconfigured system certificate store, causing
# "CERTIFICATE_VERIFY_FAILED" on every HTTPS request otherwise.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

_OEIS_SEARCH_URL = "https://oeis.org/search"
_MAX_TERMS = 40


class OEISResult(TypedDict, total=False):
    status: str
    query: str
    matches: list
    message: str


def _parse_sequence(raw: str) -> Optional[List[int]]:
    parts = [p for p in raw.replace(",", " ").split() if p]
    if not parts or len(parts) > _MAX_TERMS:
        return None
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None


def lookup_sequence(raw_sequence: str, timeout_s: int = 10) -> OEISResult:
    """Queries the real OEIS database for a given integer sequence."""
    terms = _parse_sequence(raw_sequence)
    if not terms:
        return {"status": "error", "message": "Sequence samajh nahi aayi — comma ya space se alag numbers do (max 40)."}

    query_str = ",".join(str(t) for t in terms)
    url = f"{_OEIS_SEARCH_URL}?{urllib.parse.urlencode({'q': query_str, 'fmt': 'json'})}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TrueMath/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s, context=_SSL_CONTEXT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        logger.warning(f"OEIS lookup failed (network): {e}")
        return {"status": "error", "message": "OEIS se connect nahi ho saka — internet check karein."}
    except Exception as e:
        logger.warning(f"OEIS lookup failed: {e}")
        return {"status": "error", "message": "OEIS lookup mein error aa gaya."}

    if not data or data.get("count", 0) == 0 or not data.get("results"):
        return {
            "status": "ok",
            "query": query_str,
            "matches": [],
            "message": "Koi match nahi mila OEIS mein — iska matlab ye 'naya' nahi, bas OEIS mein submit nahi hui.",
        }

    matches = []
    for entry in data["results"][:5]:
        matches.append({
            "oeis_id": entry.get("number") and f"A{entry['number']:06d}",
            "name": entry.get("name"),
        })

    return {"status": "ok", "query": query_str, "matches": matches, "message": f"{len(data['results'])} match(es) mile OEIS mein."}
