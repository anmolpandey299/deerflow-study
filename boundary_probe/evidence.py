"""Evidence segments, checkable items, URL provenance and the evidence funnel.

A *segment* is one source-linked unit of tool output exactly as the model received
it: one search hit (snippet + title + link) or one crawled page (<= 1,000 chars).
Every segment keeps (run_id, tool_seq, url) so any passage used in an
intervention or audit can be traced back to the raw tool record.
"""

from __future__ import annotations

import json
import re
from typing import Any

# numbers such as 62.7, 62.7%, 3x, 1,000, $0.40, 128K; years handled separately
NUM_RE = re.compile(r"(?<![\w.])\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|(?<![\w.])\$?\d+(?:\.\d+)?(?:%|x|×|[kKMBbT]\b)?")
YEAR_RE = re.compile(r"^(19|20)\d\d$")
URL_RE = re.compile(r"https?://[^\s)\]>\"'`]+")
# identifiers whose digits are not claims: URLs, DOIs, arXiv ids, e-mail addresses
NON_CLAIM_RE = re.compile(r"https?://\S+|\b10\.\d{4,}/\S+|\b\d{4}\.\d{4,5}(v\d+)?\b|\S+@\S+")
DDG_HIT_RE = re.compile(r"snippet: (.*?), title: (.*?), link: (\S+?)(?=, snippet: |$)", re.S)
_MULT = {"k": 1e3, "K": 1e3, "M": 1e6, "B": 1e9, "b": 1e9, "T": 1e12}
_NUM_WORDS = [(r"(\d)\s*(?:trillion)\b", r"\1T"), (r"(\d)\s*(?:billion|bn)\b", r"\1B"),
              (r"(\d)\s*(?:million|mn)\b", r"\1M"), (r"(\d)\s*(?:thousand)\b", r"\1k")]
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def normalize_url(url: str) -> str:
    url = url.strip().rstrip(".,;:)]}>'\"")
    url = url.split("#", 1)[0]
    url = re.sub(r"^https?://(www\.)?", "", url)
    return url.rstrip("/").lower()


def urls_in(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def _value(tok: str) -> float:
    core = tok.strip("$%xX×").replace(",", "")
    mult = _MULT.get(core[-1], 1.0) if core and core[-1] in _MULT else 1.0
    return float(core.rstrip("kKMBbT")) * mult


def _tolerance(tok: str) -> float:
    """Half a unit in the token's last stated digit, so '47B' matches '46.7B' (rounding)."""
    core = tok.strip("$%xX×").replace(",", "").rstrip("kKMBbT")
    decimals = len(core.split(".")[1]) if "." in core else 0
    mult = _MULT.get(tok.strip("$%xX×")[-1:], 1.0)
    return 0.5 * 10 ** (-decimals) * mult


def _numbers(text: str) -> list[str]:
    text = NON_CLAIM_RE.sub(" ", text or "")
    for pat, rep in _NUM_WORDS:
        text = re.sub(pat, rep, text, flags=re.I)
    return [m.group(0) for m in NUM_RE.finditer(text)]


def checkable_items(text: str) -> list[str]:
    """Numeric items worth checking: not bare years, not single digits without a unit, not
    digits inside URLs, DOIs, arXiv ids, e-mail addresses or markdown link texts (source
    titles such as 'Mixtral 8x7B' are not claims)."""
    out = []
    for tok in _numbers(MD_LINK_RE.sub(" ", text or "")):
        core = tok.strip("$%xX×kKMBbT").replace(",", "")
        if YEAR_RE.match(core):
            continue
        if re.fullmatch(r"\d", core) and tok == core:
            continue
        out.append(tok)
    return list(dict.fromkeys(out))


def item_present(item: str, text: str) -> bool:
    """True if a number with the same value appears (25k matches 25,000; 745B matches
    '745 billion'; 47B matches 46.7B because the item states no decimals)."""
    try:
        target, tol = _value(item), _tolerance(item)
    except ValueError:
        return False
    for tok in _numbers(text):
        try:
            if abs(_value(tok) - target) <= max(tol, 1e-9 * max(1.0, abs(target))):
                return True
        except ValueError:
            continue
    return False


def step_namespaces(run: dict[str, Any]) -> list[str]:
    """Researcher task namespaces in execution order; index == step index."""
    seen: list[str] = []
    for c in run["llm_calls"]:
        if c.get("role") == "researcher" and c.get("ns"):
            top = c["ns"].split("|")[0]
            if top not in seen:
                seen.append(top)
    return seen


def segments(run: dict[str, Any]) -> list[dict[str, Any]]:
    steps = step_namespaces(run)
    out = []
    # tool_idx = line position in tool_calls.jsonl: immutable, unique even for the
    # pilot run recorded before seq was assigned under a lock (amendment A4)
    for idx, rec in enumerate(run["tool_calls"]):
        if rec.get("error") or rec.get("content") is None:
            continue
        top = (rec.get("ns") or "").split("|")[0]
        role = top.split(":")[0] if top else None
        step = steps.index(top) if top in steps else None
        base = {"run_id": run["run_id"], "tool_idx": idx, "tool_seq": rec["seq"], "tool": rec["tool"],
                "role": role, "step": step, "args": rec["args"]}
        if rec["tool"] == "web_search":
            hits = rec.get("artifact")
            if not isinstance(hits, list):
                hits = [{"snippet": s, "title": t, "link": l}
                        for s, t, l in DDG_HIT_RE.findall(str(rec["content"]))]
            for j, h in enumerate(hits):
                out.append({**base, "seg_id": f"{idx}.{j}", "url": h.get("link"),
                            "title": h.get("title"), "text": h.get("snippet") or ""})
        elif rec["tool"] == "crawl_tool":
            try:
                data = json.loads(rec["content"])
            except (TypeError, json.JSONDecodeError):
                data = {"url": rec["args"].get("url"), "crawled_content": str(rec["content"])}
            text = data.get("crawled_content") or data.get("error") or ""
            title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), None)
            out.append({**base, "seg_id": f"{idx}.0", "url": data.get("url") or rec["args"].get("url"),
                        "title": title, "text": text})
    return out


def evidence_pool_text(run: dict[str, Any]) -> str:
    """Everything the models were shown by tools, including search-result titles."""
    return "\n".join(f"{s.get('title') or ''}\n{s['text']}" for s in segments(run))


def pool_urls(run: dict[str, Any]) -> set[str]:
    urls = {normalize_url(s["url"]) for s in segments(run) if s.get("url")}
    for s in segments(run):  # links that appear inside crawled text also count as retrieved
        urls.update(normalize_url(u) for u in urls_in(s["text"]))
    return urls


def url_provenance(report: str, run: dict[str, Any]) -> dict[str, Any]:
    found = list(dict.fromkeys(normalize_url(u) for u in urls_in(report)))
    pool = pool_urls(run)
    fabricated = [u for u in found if u not in pool]
    return {"report_urls": len(found), "urls_in_retrieved_evidence": len(found) - len(fabricated),
            "fabricated_urls": fabricated,
            "provenance_rate": None if not found else (len(found) - len(fabricated)) / len(found)}
