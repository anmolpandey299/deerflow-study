"""P3-proxy v1: a *proxy* for the brief's three axes. Not the benchmark judge.

  FMT  deterministic structure checks derived from DeerFlow's reporter prompt
  FACT (a) URL provenance vs. this run's recorded tool outputs (deterministic)
       (b) claim support: judge extracts <= max_claims central claims (verbatim
           report quotes), then labels each against the run's evidence pool; a
           SUPPORTED label counts only if its quote is found in the cited passage
  COMP pre-registered requirements labelled FULL / PARTIAL / ABSENT with a report
       quote; the primary score counts a label only if its quote is verified

Axes are reported separately and never summed.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections import Counter
from typing import Any

import httpx

from .evidence import checkable_items, evidence_pool_text, item_present, segments, url_provenance
from .settings import sha256_text

EVALUATOR = "P3-proxy-v1"

# ---------------------------------------------------------------- FMT -------
_HEADING = re.compile(r"^\s*(#{1,6})\s+(.*)$|^\s*\*\*([^*]+)\*\*\s*:?\s*$")


def _headings(report: str) -> list[tuple[int, str]]:
    out = []
    for i, line in enumerate(report.splitlines()):
        m = _HEADING.match(line)
        if m:
            out.append((i, (m.group(2) or m.group(3) or "").strip().lower()))
    return out


def format_checks(report: str) -> dict[str, Any]:
    lines = report.splitlines()
    heads = _headings(report)
    find = lambda pat: next((i for i, h in heads if re.search(pat, h)), None)  # noqa: E731
    kc, kp, ov, da, ref = (find(r"key citations"), find(r"key points"), find(r"overview"),
                           find(r"detailed analysis"), find(r"references|citations"))
    first = next((ln for ln in lines if ln.strip()), "")
    bullets = 0
    if kp is not None:
        nxt = next((i for i, _ in heads if i > kp), len(lines))
        bullets = sum(1 for ln in lines[kp + 1:nxt] if re.match(r"^\s*([-*+]|\d+\.)\s+", ln))
    last_ref = max((i for i, h in heads if re.search(r"references|citations", h)), default=None)
    checks = {
        "h1_title": first.startswith("# "),
        "key_citations_before_key_points": kc is not None and (kp is None or kc < kp),
        "key_points_4_to_6_bullets": 4 <= bullets <= 6,
        "overview_section": ov is not None,
        "detailed_analysis_section": da is not None,
        "references_with_urls": last_ref is not None and "http" in "\n".join(lines[last_ref:]),
        "markdown_table": any(re.match(r"^\s*\|?\s*:?-{3,}", ln) for ln in lines),
        "no_wrapping_code_fence": not first.strip().startswith("```"),
    }
    return {"checks": checks, "score": sum(checks.values()) / len(checks)}


# ------------------------------------------------------------ judge I/O -----
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = {ord("‘"): "'", ord("’"): "'", ord("“"): '"', ord("”"): '"'}


def _norm(text: str) -> str:
    # NFKC folds narrow/no-break spaces; judges (gpt-oss) emit U+2011 / U+202F freely
    text = unicodedata.normalize("NFKC", text or "").translate(_DASHES).translate(_QUOTES)
    text = re.sub(r"[*_`#>|\[\]()]", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[.,][0-9]+)*%?", _norm(text))


def quote_found(quote: str, source: str) -> bool:
    """Verbatim after normalisation (tolerating an ellipsis), or - because judges
    paraphrase a word or two - at least 80% of the quote's tokens inside one local
    window of the source with every number matching exactly (amendment A9)."""
    q = _norm(quote).strip(". ")
    if len(q) < 8:
        return False
    src = _norm(source)
    if all(part.strip() in src for part in q.split("...") if part.strip()):
        return True
    qt = _tokens(quote)
    if len(qt) < 8:
        return False
    nums = {t for t in qt if any(c.isdigit() for c in t)}
    st = _tokens(source)
    width = int(len(qt) * 1.5) + 1
    need = Counter(qt)
    for i in range(max(1, len(st) - width + 1)):
        window = Counter(st[i:i + width])
        if sum(min(c, window[t]) for t, c in need.items()) >= 0.8 * len(qt) and nums <= set(window):
            return True
    return False


def extract_json(text: str) -> dict[str, Any]:
    """Last top-level JSON object in `text` (tolerates prose or code fences around it)."""
    text = re.sub(r"```(?:json)?", "", text or "")
    depth, start, last = 0, None, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0:
                last = text[start:i + 1]
    if last is None:
        raise ValueError("no JSON object in judge output")
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        pass
    # gpt-oss free-text JSON: stray quotes between array elements ("},"{"), observed in A9
    cleaned = re.sub(r'\}\s*"?\s*,\s*"\s*\{', '},{', last)
    cleaned = re.sub(r'\}\s*"\s*,', '},', cleaned)
    cleaned = re.sub(r'\}\s*"\s*\]', '}]', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:  # e.g. unescaped quotes copied from the report
        from json_repair import repair_json  # same library DeerFlow uses for planner JSON
        return json.loads(repair_json(cleaned))


class Judge:
    def __init__(self, cfg: dict[str, Any], model: str | None = None):
        j = cfg["judge"]
        self.model = model or j["model"]
        self.base = cfg["model"]["base_url"].rsplit("/v1", 1)[0]
        self.options = {"temperature": j["temperature"], "seed": j["seed"], "num_ctx": j["num_ctx"]}
        self.think = j.get("think")
        # grammar-constrained decoding ("format") vs. free text + JSON extraction; see amendment A9
        self.structured = j.get("structured_output", True)
        self.usage: list[dict[str, Any]] = []

    def __call__(self, system: str, user: str, schema: dict[str, Any], name: str) -> dict[str, Any]:
        body = {"model": self.model, "stream": False, "options": self.options,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if self.structured:
            body["format"] = schema
        else:
            body["messages"][1]["content"] += ("\n\nRespond with a single JSON object matching this schema "
                                               "and nothing else:\n" + json.dumps(schema))
        if self.think is not None and "gpt-oss" in self.model:
            body["think"] = self.think
        t0 = time.time()
        r = httpx.post(f"{self.base}/api/chat", json=body, timeout=1800).json()
        if "message" not in r:
            raise RuntimeError(f"judge error: {r}")
        self.usage.append({"call": name, "prompt_tokens": r.get("prompt_eval_count"),
                           "completion_tokens": r.get("eval_count"), "wall_s": time.time() - t0,
                           "thinking_chars": len(r["message"].get("thinking") or "")})
        content = r["message"]["content"]
        out = json.loads(content) if self.structured else extract_json(content)
        if isinstance(out, list):  # a bare array for a single-array schema
            out = {schema["required"][0]: out}
        return out


# ------------------------------------------------------------ COMP ----------
COMP_SYSTEM = (
    "You evaluate whether a research report satisfies specific requirements. Judge only what the "
    "report text says; do not use outside knowledge and do not judge whether it is true. For each "
    "requirement answer FULL (clearly and specifically satisfied), PARTIAL (addressed but vague, "
    "generic or incomplete) or ABSENT. For FULL or PARTIAL copy one short verbatim excerpt "
    "(at most 40 words) from the report that best shows it; for ABSENT use an empty string.")
COMP_SCHEMA = {"type": "object", "required": ["labels"], "properties": {"labels": {
    "type": "array", "items": {"type": "object", "required": ["id", "label", "quote"], "properties": {
        "id": {"type": "string"}, "label": {"type": "string", "enum": ["FULL", "PARTIAL", "ABSENT"]},
        "quote": {"type": "string"}}}}}}


def completeness(judge: Judge, report: str, query: dict[str, Any]) -> dict[str, Any]:
    reqs = "\n".join(f"{r['id']}: {r['text']}" for r in query["requirements"])
    out = judge(COMP_SYSTEM, f"Query: {query['text']}\n\nRequirements:\n{reqs}\n\n"
                f"Report:\n<<<\n{report}\n>>>", COMP_SCHEMA, "completeness")
    by_id = {x["id"]: x for x in out.get("labels", [])}
    rows, strict, lenient = [], 0.0, 0.0
    for r in query["requirements"]:
        x = by_id.get(r["id"], {"label": "ABSENT", "quote": ""})
        verified = x["label"] == "ABSENT" or quote_found(x["quote"], report)
        w = {"FULL": 1.0, "PARTIAL": 0.5, "ABSENT": 0.0}[x["label"]]
        lenient += w
        strict += w if verified else 0.0
        rows.append({"id": r["id"], "label": x["label"], "quote": x["quote"], "quote_verified": verified})
    n = len(query["requirements"])
    return {"labels": rows, "score": strict / n, "score_lenient": lenient / n}


# ------------------------------------------------------------ FACT ----------
CLAIM_SYSTEM = (
    "Extract the most central checkable factual claims from a research report: prefer claims with "
    "numbers, benchmark results, named comparisons or attributions to a specific method, paper or "
    "product. Skip opinions and generic statements. For each claim copy the sentence (or table row) "
    "verbatim from the report as report_quote, then restate the claim in one self-contained sentence.")
CLAIM_SCHEMA = {"type": "object", "required": ["claims"], "properties": {"claims": {
    "type": "array", "items": {"type": "object", "required": ["report_quote", "claim"], "properties": {
        "report_quote": {"type": "string"}, "claim": {"type": "string"}}}}}}
VERIFY_SYSTEM = (
    "You check claims against numbered evidence passages that a research system retrieved. Use only "
    "the passages, never outside knowledge. Label each claim SUPPORTED (a passage explicitly states "
    "it, including any numbers), CONTRADICTED (a passage states something incompatible) or NOT_FOUND "
    "(no passage addresses it). For SUPPORTED or CONTRADICTED give the passage id and one verbatim "
    "excerpt (at most 40 words) from that passage; otherwise use empty strings.")
VERIFY_SCHEMA = {"type": "object", "required": ["verdicts"], "properties": {"verdicts": {
    "type": "array", "items": {"type": "object", "required": ["claim_index", "label", "evidence_id", "quote"],
                               "properties": {"claim_index": {"type": "integer"},
                                              "label": {"type": "string", "enum": ["SUPPORTED", "CONTRADICTED", "NOT_FOUND"]},
                                              "evidence_id": {"type": "string"}, "quote": {"type": "string"}}}}}}


def factuality(judge: Judge, report: str, run: dict[str, Any], max_claims: int) -> dict[str, Any]:
    raw = judge(CLAIM_SYSTEM, f"Return at most {max_claims} claims.\n\nReport:\n<<<\n{report}\n>>>",
                CLAIM_SCHEMA, "claims").get("claims", [])[:max_claims]
    claims = [c for c in raw if quote_found(c["report_quote"], report)]
    segs = {f"E{k}": s for k, s in enumerate(segments(run))}
    rows = []
    if claims:
        evidence = "\n\n".join(f"[{k}] {s.get('title') or ''} ({s.get('url') or ''})\n{s['text']}"
                               for k, s in segs.items())
        listing = "\n".join(f"{i}. {c['claim']}" for i, c in enumerate(claims))
        verdicts = judge(VERIFY_SYSTEM, f"Evidence passages:\n{evidence}\n\nClaims:\n{listing}",
                         VERIFY_SCHEMA, "verify").get("verdicts", [])
        by_i = {v["claim_index"]: v for v in verdicts}
        for i, c in enumerate(claims):
            v = by_i.get(i, {"label": "NOT_FOUND", "evidence_id": "", "quote": ""})
            seg = segs.get(v.get("evidence_id", "").strip("[]"))
            verified = v["label"] == "NOT_FOUND" or (seg is not None and quote_found(v["quote"], seg["text"]))
            rows.append({**c, "label": v["label"], "evidence_id": v.get("evidence_id"),
                         "evidence_url": seg.get("url") if seg else None, "quote": v.get("quote"),
                         "quote_verified": verified,
                         "counted_supported": v["label"] == "SUPPORTED" and verified})
    supported = sum(r["counted_supported"] for r in rows)
    return {"claims_extracted": len(raw), "claims_checked": len(rows), "claims": rows,
            "supported": supported,
            "contradicted": sum(r["label"] == "CONTRADICTED" for r in rows),
            "unsupported": len(rows) - supported,
            "score": None if not rows else supported / len(rows)}


# ------------------------------------------------------------ entry ---------
def judge_settings(judge: Judge) -> dict[str, Any]:
    return {"think": judge.think, "structured_output": judge.structured, "options": judge.options,
            "prompt_sha256": {"comp": sha256_text(COMP_SYSTEM), "claims": sha256_text(CLAIM_SYSTEM),
                              "verify": sha256_text(VERIFY_SYSTEM)}}


def evaluate(report: str, run: dict[str, Any], query: dict[str, Any], cfg: dict[str, Any],
             judge: Judge | None) -> dict[str, Any]:
    pool = evidence_pool_text(run)
    nums = checkable_items(report)
    out = {
        "evaluator": EVALUATOR, "report_sha256": sha256_text(report),
        "report_chars": len(report), "report_words": len(report.split()),
        "fmt": format_checks(report),
        "fact_url": url_provenance(report, run),
        "numeric_items": len(nums),
        "numeric_items_not_in_evidence": [n for n in nums if not item_present(n, pool)],
    }
    if judge is not None:
        out["judge_model"] = judge.model
        out["judge_settings"] = judge_settings(judge)
        out["comp"] = completeness(judge, report, query)
        out["fact_claims"] = factuality(judge, report, run, cfg["judge"]["max_claims"])
        out["judge_usage"] = judge.usage
    return out


# ------------------------------------------------------------ CLI -----------
def _eval_one(report: str, run: dict[str, Any], query: dict[str, Any], cfg: dict[str, Any],
              judge_model: str | None, out_path, meta: dict[str, Any]) -> dict[str, Any]:
    from pathlib import Path

    out_path = Path(out_path)
    sha = sha256_text(report)
    judge = Judge(cfg, judge_model) if judge_model else None
    if out_path.exists():  # reuse only a result made from the same report, evaluator and judge settings
        prev = json.loads(out_path.read_text())
        if prev.get("report_sha256") == sha and prev.get("evaluator") == EVALUATOR and \
                prev.get("judge_model") == judge_model and \
                prev.get("judge_settings") == (judge_settings(judge) if judge else None):
            return prev
    t0 = time.time()
    res = {**meta, **evaluate(report, run, query, cfg, judge), "eval_wall_s": time.time() - t0}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


def main() -> None:
    import argparse
    from pathlib import Path

    from .boundary import load_run
    from .settings import ANALYSIS_DIR, load_config, load_queries

    ap = argparse.ArgumentParser(description="P3-proxy v1 evaluation (proxy, not the benchmark judge)")
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--replays", action="store_true", help="evaluate replay reports instead of the baseline")
    ap.add_argument("--judge-model", default=None, help="omit for deterministic checks only")
    ap.add_argument("--seeds", type=int, nargs="*", default=None,
                    help="replay seeds to evaluate (A9: full P3 on seed 101; default all)")
    ap.add_argument("--cases", nargs="*", default=None, help="replay case ids to evaluate (default all)")
    args = ap.parse_args()
    cfg, queries = load_config(), load_queries()
    for d in args.run_dirs:
        run = load_run(Path(d))
        q = queries[run["manifest"]["query_id"]]
        base = ANALYSIS_DIR / "evals" / run["run_id"]
        if not args.replays:
            r = _eval_one(run["report"], run, q, cfg, args.judge_model, base / "baseline.json",
                          {"run_id": run["run_id"], "kind": "baseline"})
            print(run["run_id"], "baseline", _brief(r), flush=True)
            continue
        for f in sorted((Path(d) / "replays").glob("*/*-s*.json")):
            rep = json.loads(f.read_text())
            if (args.seeds is not None and rep["seed"] not in args.seeds) or \
                    (args.cases is not None and rep["case_id"] not in args.cases):
                continue
            r = _eval_one(rep["content"], run, q, cfg, args.judge_model,
                          base / rep["case_id"] / f.name,
                          {"run_id": run["run_id"], "kind": "replay", "case_id": rep["case_id"],
                           "condition": rep["condition"], "seed": rep["seed"]})
            print(run["run_id"], rep["case_id"], f.stem, _brief(r), flush=True)


def _brief(r: dict[str, Any]) -> str:
    parts = [f"FMT={r['fmt']['score']:.2f}", f"URLprov={r['fact_url']['provenance_rate']}"]
    if "comp" in r:
        parts += [f"COMP={r['comp']['score']:.2f}", f"FACTb={r['fact_claims']['score']}",
                  f"unsupported={r['fact_claims']['unsupported']}"]
    return " ".join(parts)


if __name__ == "__main__":
    main()
