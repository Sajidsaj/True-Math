"""
Module Name: web_search_fallback
Purpose: Real web search via DuckDuckGo (using the `ddgs` library), which
         needs no API key. Used as a FALLBACK when the Q&A box's LLM
         providers (Groq/OpenRouter) are all unavailable — rate-limited,
         misconfigured, or offline — so the user gets real search results
         (titles, snippets, links) instead of a hard error with nothing.
Dependencies: ddgs
Honesty note: This returns raw search result snippets, NOT an AI-generated
              answer — there is no synthesis or reasoning step. It's a
              genuinely different (and more limited) kind of help than the
              LLM tutor: pointers to read, not a worked answer. It exists
              specifically so a rate-limited AI provider doesn't leave the
              user with nothing at all.
"""
from __future__ import annotations

from typing import TypedDict

from src.core.sys_logger import get_logger

logger = get_logger("WebSearchFallback")


class WebSearchResult(TypedDict, total=False):
    status: str
    query: str
    results: list
    message: str


def search_web(query: str, max_results: int = 5, timeout_s: int = 10) -> WebSearchResult:
    """Searches DuckDuckGo (no API key needed) and returns raw results.
    This is intentionally NOT an AI-generated answer — just real search
    result snippets, used as a fallback when the LLM providers are down."""
    query = (query or "").strip()
    if not query:
        return {"status": "error", "message": "Search query khaali hai."}

    try:
        from ddgs import DDGS
    except ImportError:
        return {"status": "error", "message": "ddgs library install nahi hai (pip install ddgs)."}

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max(1, min(max_results, 10))))
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return {"status": "error", "message": f"Web search fail ho gaya: {e}"}

    if not raw_results:
        return {"status": "ok", "query": query, "results": [], "message": f"'{query}' ke liye koi result nahi mila."}

    results = [
        {
            "title": r.get("title", ""),
            "snippet": r.get("body", ""),
            "link": r.get("href", ""),
        }
        for r in raw_results
    ]
    return {"status": "ok", "query": query, "results": results, "message": f"{len(results)} web result(s) mile (DuckDuckGo se, AI-generated nahi)."}
