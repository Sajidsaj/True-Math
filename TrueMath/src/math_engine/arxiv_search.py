"""
Module Name: arxiv_search
Purpose: Real-time search of arXiv.org's math section — actual, current
         research papers (many posted within days), using arXiv's public
         Atom API. This is genuine live internet data, not cached or
         simulated — it's how you keep a math tool aware of math that is
         actively being developed right now.
Responsibilities:
  - Query the real arXiv API for a topic, sorted by most recent submission.
  - Parse the Atom XML response into a clean list of papers (title,
    authors, date, abstract, link).
Dependencies: urllib, xml.etree.ElementTree (both stdlib — no extra deps)
Honesty note: This surfaces REAL current research — but a paper existing
              on arXiv doesn't mean its claims are settled; arXiv preprints
              are not peer-reviewed at the time of posting. Treat results
              as pointers to current research activity, not verified fact.
"""
from __future__ import annotations

import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import TypedDict

import certifi

# Uses certifi's CA bundle explicitly rather than relying on the system's
# default certificate store — on some Windows Python installs, the system
# store is missing/misconfigured, causing a "CERTIFICATE_VERIFY_FAILED:
# unable to get local issuer certificate" error on every HTTPS request.
# This is a common, well-known Windows Python issue, not specific to arXiv.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

_ARXIV_API = "https://export.arxiv.org/api/query"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_MAX_SUMMARY_CHARS = 400


class ArxivResult(TypedDict, total=False):
    status: str
    query: str
    papers: list
    message: str


def search_arxiv(query: str, max_results: int = 5, timeout_s: int = 15) -> ArxivResult:
    """Searches arXiv's math + related categories for `query`, sorted by
    most recently submitted first — so you see what's actively being
    published right now on the topic."""
    query = (query or "").strip()
    if not query:
        return {"status": "error", "message": "Search query khaali hai."}

    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max(1, min(max_results, 20)),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{_ARXIV_API}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TrueMath/1.0 (personal research tool)"})
        with urllib.request.urlopen(req, timeout=timeout_s, context=_SSL_CONTEXT) as resp:
            xml_data = resp.read()
    except urllib.error.URLError as e:
        return {"status": "error", "message": f"arXiv se connect nahi ho saka — internet check karein. ({e})"}
    except Exception as e:
        return {"status": "error", "message": f"arXiv lookup mein error: {e}"}

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        return {"status": "error", "message": f"arXiv response parse nahi ho saka: {e}"}

    papers = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        title = (entry.findtext("atom:title", default="", namespaces=_ATOM_NS) or "").strip().replace("\n", " ")
        summary = (entry.findtext("atom:summary", default="", namespaces=_ATOM_NS) or "").strip().replace("\n", " ")
        if len(summary) > _MAX_SUMMARY_CHARS:
            summary = summary[:_MAX_SUMMARY_CHARS] + "…"
        published = (entry.findtext("atom:published", default="", namespaces=_ATOM_NS) or "")[:10]
        link = entry.findtext("atom:id", default="", namespaces=_ATOM_NS) or ""
        authors = [
            (a.findtext("atom:name", default="", namespaces=_ATOM_NS) or "")
            for a in entry.findall("atom:author", _ATOM_NS)
        ]
        papers.append({
            "title": title,
            "authors": authors[:5],
            "published": published,
            "summary": summary,
            "link": link,
        })

    if not papers:
        return {"status": "ok", "query": query, "papers": [], "message": f"'{query}' ke liye koi recent paper nahi mila arXiv par."}
    return {"status": "ok", "query": query, "papers": papers, "message": f"{len(papers)} recent paper(s) mile arXiv par (naye se purane)."}
