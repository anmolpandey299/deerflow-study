"""Post-hoc rechecks of published figures, added by the integrity review of 2026-10-01.

    python -m boundary_probe.rechecks      # -> analysis/rechecks.json and analysis/rechecks.md

Every check reads the recorded runs and pilot outputs and writes nothing else. Each one prints the
figure as originally published beside the recomputed one. None of them replaces a pre-registered result;
they qualify how a published number should be read.
"""

from __future__ import annotations

import csv
import json
import re
import statistics as st
from math import comb
from typing import Any

from .boundary import load_run, observation_indices, reporter_call
from .evidence import _numbers, _tolerance, _value, checkable_items, evidence_pool_text, item_present
from .settings import ANALYSIS_DIR, ROOT, RUNS_DIR
from .tables import WARNING, origins, relay_row, step_kinds

PILOT_OUT = ROOT / "part2_pilot" / "outputs"

DATE_TIME = re.compile(
    r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*,?\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{1,2},?"
    r"\s+\d{4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?|\b\d{1,2}:\d{2}(?::\d{2})?\b")
ERROR_CODE = re.compile(r"\b(?:os error|error|errno|status(?: code)?|HTTP(?:/\d\.\d)?)\s*:?\s*\d{2,3}\b", re.I)
VERSION = re.compile(r"\b(?:Apache|GPL|LGPL|AGPL|MPL|CC[- ]BY(?:[- ](?:SA|NC|ND))*)[- ]?\d+(?:\.\d+)+\b"
                     r"|\bv(?:ersion)?\s?\d+(?:\.\d+)+\b", re.I)
EXAMPLE = re.compile(r"\be\.g\.,?[^)\n]{0,60}", re.I)


def completed_runs() -> list[dict[str, Any]]:
    runs = []
    for d in sorted(RUNS_DIR.iterdir()):
        m = d / "raw" / "manifest.json"
        if m.exists() and not (d / "EXCLUDED.txt").exists() and json.loads(m.read_text())["status"] == "completed":
            runs.append(load_run(d))
    return runs


def clean(text: str, drop_examples: bool = False) -> str:
    """Remove dates and clock times, HTTP and OS error codes and version numbers, whose digits are not claims."""
    text = VERSION.sub(" ", ERROR_CODE.sub(" ", DATE_TIME.sub(" ", text or "")))
    return EXAMPLE.sub(" ", text) if drop_examples else text


def unit(tok: str) -> str:
    m = re.search(r"(%|x|×|[kKMBbT])$", tok.strip("$"))
    return {"×": "x", "k": "K", "b": "B"}.get(m.group(1), m.group(1)) if m else ""


def specific(tok: str) -> bool:
    """A unit, a currency sign, a decimal point, or an integer of at least 100."""
    core = tok.strip("$%xX×kKMBbT").replace(",", "")
    return bool(unit(tok)) or tok.startswith("$") or "." in core or float(core) >= 100


def present(item: str, text: str, same_unit: bool = False) -> bool:
    if not same_unit:
        return item_present(item, text)
    target, tol = _value(item), _tolerance(item)
    for tok in _numbers(text):
        try:
            if unit(tok) == unit(item) and abs(_value(tok) - target) <= max(tol, 1e-9 * max(1.0, abs(target))):
                return True
        except ValueError:
            continue
    return False


def relay_variant(run: dict[str, Any], variant: int) -> dict[str, Any]:
    """E10 relay under four item definitions. Variant 0 is the published table (tables.relay_row).

    1: dates, clock times, error codes and version numbers removed; same-value items counted once.
    2: as 1, also dropping unitless integers below 100 and values inside "e.g." examples.
    3: as 2, but a report number matches only with the same unit (none, %, x, K, M, B, T).
    """
    if variant == 0:
        r = relay_row(run)
        return {"run_id": run["run_id"], **{f"{k}_{s}": r[f"{k2}_in_{s2}"] for k, k2 in
                (("grounded", "grounded"), ("warned", "ungrounded_in_warned_step"), ("other", "ungrounded_other"))
                for s, s2 in (("obs", "observations"), ("rep", "report"))}}
    strict = variant >= 2
    pool, rep = clean(evidence_pool_text(run)), clean(run["report"])
    obs_raw = run["final_state"].get("observations") or []
    obs = [clean(o, drop_examples=strict) for o in obs_raw]
    seen, items = set(), []
    for i in sorted(dict.fromkeys(i for o in obs for i in checkable_items(o)), key=lambda x: (-len(unit(x)), x)):
        v = round(_value(i), 9)
        if v not in seen:
            seen.add(v)
            items.append(i)
    if strict:
        items = [i for i in items if specific(i)]
    row = {"run_id": run["run_id"], **{f"{k}_{s}": 0 for k in ("grounded", "warned", "other") for s in ("obs", "rep")}}
    for i in items:
        if item_present(i, pool):
            k = "grounded"
        elif any(WARNING in ro and item_present(i, o) for ro, o in zip(obs_raw, obs)):
            k = "warned"
        else:
            k = "other"
        row[f"{k}_obs"] += 1
        row[f"{k}_rep"] += int(present(i, rep, same_unit=variant >= 3))
    return row


def relay(runs: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for v in range(4):
        rows = [relay_variant(r, v) for r in runs]
        tot = {k: sum(r[k] for r in rows) for k in rows[0] if k != "run_id"}
        out[f"variant_{v}"] = {"totals": tot, "rows": rows}
    return out


def report_numbers(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """E6 under the E10 item definitions: report numbers found in no retrieved text, by the step where they first appear.

    Variant 0 is the published table (tables.origins); variants 1-3 clean the report and the pool as in relay_variant.
    Each variant is also given without q03-r01, the run degraded by the network outage.
    """
    out = {}
    for v in range(4):
        rows = []
        for run in runs:
            if v == 0:
                o = origins(run)
                row = {"report_numbers": o["report_numbers"], "unmatched": o["numbers_in_no_tool_output"],
                       "by_first_origin": o["by_first_origin"]}
            else:
                pool = clean(evidence_pool_text(run))
                seen, items = set(), []
                for i in sorted(dict.fromkeys(checkable_items(clean(run["report"], drop_examples=v >= 2))),
                                key=lambda x: (-len(unit(x)), x)):
                    if round(_value(i), 9) not in seen:
                        seen.add(round(_value(i), 9))
                        items.append(i)
                items = [i for i in items if specific(i)] if v >= 2 else items
                obs, kinds = run["final_state"].get("observations") or [], step_kinds(run)
                by: dict[str, int] = {}
                for i in items:
                    if not present(i, pool, same_unit=v >= 3):
                        k = next((kinds[j] for j, o in enumerate(obs) if item_present(i, o)), "reporter (in no observation)")
                        by[k] = by.get(k, 0) + 1
                row = {"report_numbers": len(items), "unmatched": sum(by.values()), "by_first_origin": by}
            rows.append({"run_id": run["run_id"], "outage": (RUNS_DIR / run["run_id"] / "FLAG_OUTAGE_AFFECTED.txt").exists(), **row})
        tot = lambda rs: {"report_numbers": sum(r["report_numbers"] for r in rs), "unmatched": sum(r["unmatched"] for r in rs),  # noqa: E731
                          "by_first_origin": {k: sum(r["by_first_origin"].get(k, 0) for r in rs)
                                              for k in sorted({k for r in rs for k in r["by_first_origin"]})}}
        out[f"variant_{v}"] = {"totals": tot(rows), "without_outage_run": tot([r for r in rows if not r["outage"]]), "rows": rows}
    return out


def crawl(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """E9 at page level. A crawl is an error page if its text is a fetch failure, block, CAPTCHA, 404 or empty."""
    bad = re.compile(r"Non-HTML Content|No content could be extracted|Are you a robot|404: Page not found|ApX logo")
    pages = [{"run_id": r["run_id"], "url": c["url"], "full": c["full_chars"], "shown": c["shown_chars"],
              "error_page": bool(bad.search(c.get("full_markdown", "")[:300]))} for r in runs for c in r["crawl_fulltext"]]
    real = [p for p in pages if not p["error_page"]]
    cut = [p for p in pages if p["full"] > p["shown"]]
    total = sum(p["full"] for p in pages)
    biggest = sorted(pages, key=lambda p: -p["full"])
    return {"crawls": len(pages), "error_pages": len(pages) - len(real), "real_pages": len(real), "cut": len(cut),
            "pooled_share_shown": round(sum(p["shown"] for p in pages) / total, 4),
            "real_page_share_shown_median": round(st.median(p["shown"] / p["full"] for p in real), 3),
            "real_page_share_shown_range": [round(min(p["shown"] / p["full"] for p in real), 4),
                                            round(max(p["shown"] / p["full"] for p in real), 3)],
            "share_of_characters_in_largest_5": round(sum(p["full"] for p in biggest[:5]) / total, 3),
            "pages": pages}


def system_prompt_share(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """E5: share of researcher-request characters held by system messages. Characters, not tokens."""
    rows = []
    for r in runs:
        sys_c = tot_c = copies = 0
        for c in r["llm_calls"]:
            if c["role"] != "researcher":
                continue
            msgs = c["request"]["messages"]
            text = [(m["role"], m["content"] if isinstance(m["content"], str) else json.dumps(m["content"])) for m in msgs]
            sys_c += sum(len(t) for role, t in text if role == "system")
            tot_c += sum(len(t) for _, t in text)
            copies = max(copies, sum(role == "system" for role, _ in text))
        rows.append({"run_id": r["run_id"], "system_char_share": round(sys_c / tot_c, 3), "max_system_messages": copies})
    shares = [x["system_char_share"] for x in rows]
    return {"mean": round(st.mean(shares), 3), "range": [min(shares), max(shares)], "rows": rows}


def reporter_requirements(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """K2: the reporter's first user message (plan title and thought) against the user's query."""
    words = lambda s: {w for w in re.findall(r"[a-z][a-z-]{3,}", s.lower())}  # noqa: E731
    rows = []
    for r in runs:
        msg = reporter_call(r)["request"]["messages"][1]["content"]
        q = r["manifest"]["query_text"]
        rows.append({"run_id": r["run_id"], "query_words_restated": round(len(words(q) & words(msg)) / len(words(q)), 2),
                     "thought_opens_with_user_request": bool(re.search(r"## Description\s+The user is asking", msg))})
    return {"rows": rows}


def citations(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Which recorded URLs became reporter citations: DuckDuckGo hits are plain text, so only crawls do."""
    rows = []
    for r in runs:
        cited = [c.get("url") for c in r["final_state"].get("citations") or []]
        crawled = {(t.get("args") or {}).get("url") for t in r["tool_calls"] if t["tool"] == "crawl_tool"}
        rows.append({"run_id": r["run_id"], "citations": len(cited), "from_crawls": sum(u in crawled for u in cited)})
    return {"citations": sum(x["citations"] for x in rows), "from_crawls": sum(x["from_crawls"] for x in rows), "rows": rows}


def step_costs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Model calls, prompt tokens and model time of later research steps, by whether the step searched."""
    searched = {(r["run_id"], int(r["step"])): r["searched"] == "True"
                for r in csv.DictReader(open(ANALYSIS_DIR / "tables" / "researcher_steps.csv"))}
    groups: dict[str, list[dict[str, float]]] = {"searched": [], "no_search": []}
    for r in runs:
        order: list[str] = []
        agg: dict[str, dict[str, float]] = {}
        for c in r["llm_calls"]:
            if c["role"] != "researcher":
                continue
            ns = str(c["ns"]).split("|")[0]
            if ns not in agg:
                order.append(ns)
                agg[ns] = {"calls": 0, "prompt_tokens": 0, "wall_s": 0.0}
            agg[ns]["calls"] += 1
            agg[ns]["prompt_tokens"] += int(c.get("prompt_tokens") or 0)
            agg[ns]["wall_s"] += float(c.get("wall_s") or 0)
        for i, ns in enumerate(order):
            if i > 0 and (r["run_id"], i) in searched:
                groups["searched" if searched[(r["run_id"], i)] else "no_search"].append(agg[ns])
    return {k: {"steps": len(v), **{f"median_{m}": round(st.median(x[m] for x in v), 1) for m in
                                     ("calls", "prompt_tokens", "wall_s")}} for k, v in groups.items()}


def insertion_positions() -> list[dict[str, Any]]:
    """Where the B and L blocks sit in the pilot's reporter requests."""
    out = []
    for case in ("c03", "c05"):
        for arm in ("B", "L"):
            rec = json.loads((PILOT_OUT / case / f"{arm}-s101.json").read_text())
            msgs = rec["request"]["messages"]
            i = max(int(k) for k in rec["declared_changes"])
            base = msgs[i]["content"][: len(msgs[i]["content"]) - len(rec["declared_changes"][str(i)])]
            obs = observation_indices(rec["request"])
            out.append({"case": case, "arm": arm, "message": i, "observation": obs.index(i) + 1, "observations": len(obs),
                        "after_references_list": bool(re.search(r"\n## References\b", base)),
                        "observation_chars_before": len(base)})
    return out


def binle(n: int, k: int, p: float) -> float:
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def chance(p: float, p_other: float = 0.0) -> dict[str, float]:
    """Probability that c05's pre-registered 'ledger uptake' event occurs with no ledger effect.

    L and B state the fact with probability p; A, C and LC with p_other (0 when the fact is absent from their input).
    Original rule: L >= 2 of 3, B <= 1 of 3, A <= 1 of 3, C <= 1 of 3, LC 0 of 1.
    Amendment A1: L >= 2 of 3, in-session B <= 1 of 2, LC 0 of 1.
    """
    l_up = 1 - binle(3, 1, p)
    return {"original_rule": l_up * binle(3, 1, p) * binle(3, 1, p_other) ** 2 * (1 - p_other),
            "a1_rule": l_up * binle(2, 1, p) * (1 - p_other)}


def h1b_fails(p: float, cases: int = 5) -> float:
    """Probability that H1b fails by its rule (insensitivity, B <= 1 of 3, in a majority of cases) at uptake p."""
    q = binle(3, 1, p)
    return sum(comb(cases, k) * q ** k * (1 - q) ** (cases - k) for k in range(cases // 2 + 1, cases + 1))


def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """One-sided Fisher exact p for [[a, b], [c, d]], first row higher."""
    n1, k, n = a + b, a + c, a + b + c + d
    return sum(comb(k, x) * comb(n - k, n1 - x) for x in range(a, min(k, n1) + 1)) / comb(n, n1)


def probabilities() -> dict[str, Any]:
    ps = (0.2, 1 / 3, 0.5)
    return {"c05_uptake_by_chance_no_ledger_effect": {f"{p:.2f}": {k: round(v, 3) for k, v in chance(p).items()} for p in ps},
            "h1b_fails_at_true_uptake": {f"{p:.1f}": round(h1b_fails(p), 3) for p in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8)},
            "fisher_one_sided": {"part1 B 2/15 vs A+C 0/30 (hand reading)": round(fisher_one_sided(2, 13, 0, 30), 3),
                                 "part1 B 3/15 vs A+C 0/30 (detector)": round(fisher_one_sided(3, 12, 0, 30), 3),
                                 "pilot c05 L 2/3 vs B 1/3": round(fisher_one_sided(2, 1, 1, 2), 3),
                                 "pilot c03+c05 L 2/6 vs B 1/6": round(fisher_one_sided(2, 4, 1, 5), 3)}}


def report(res: dict[str, Any]) -> str:
    v = {k: x["totals"] for k, x in res["relay"].items()}
    rate = lambda t, k: f"{t[k + '_rep']}/{t[k + '_obs']} ({t[k + '_rep'] / t[k + '_obs']:.0%})"  # noqa: E731
    lines = ["# Rechecks of published figures (generated by boundary_probe.rechecks)", "",
             "Post hoc. Each section shows the published figure and the recomputed one; no pre-registered result changes.", "",
             "## E10, relay of numbers from observations to the report", "",
             "| Item definition | Grounded in retrieved text | From flagged no-search steps | Other |", "|---|---|---|---|"]
    names = ["As published", "Minus dates, times, error codes, versions; same value once",
             "Also minus unitless integers below 100 and 'e.g.' examples", "As the row above, and a match needs the same unit"]
    for i, n in enumerate(names):
        t = v[f"variant_{i}"]
        lines.append(f"| {n} | {rate(t, 'grounded')} | {rate(t, 'warned')} | {rate(t, 'other')} |")
    lines += ["", "## E6, report numbers found in no retrieved text", "",
              "| Item definition | All 10 runs | Without the outage run | First seen in no-search or analyst steps |",
              "|---|---|---|---|"]
    for i, n in enumerate(names):
        x = res["report_numbers"][f"variant_{i}"]
        t, w, by = x["totals"], x["without_outage_run"], x["totals"]["by_first_origin"]
        early = by.get("researcher, no search", 0) + by.get("analyst (no tools)", 0)
        lines.append(f"| {n} | {t['unmatched']}/{t['report_numbers']} ({t['unmatched'] / t['report_numbers']:.0%}) | "
                     f"{w['unmatched']}/{w['report_numbers']} ({w['unmatched'] / w['report_numbers']:.0%}) | {early} |")
    c = res["crawl"]
    lines += ["", "## E9, crawl truncation", "",
              f"{c['crawls']} crawls: {c['error_pages']} error, block or empty pages and {c['real_pages']} real pages, "
              f"of which {c['cut']} were cut to 1,000 characters. Pooled share shown {c['pooled_share_shown']:.1%}; "
              f"median share shown per real page {c['real_page_share_shown_median']:.1%} "
              f"(range {c['real_page_share_shown_range'][0]:.1%}–{c['real_page_share_shown_range'][1]:.0%}); "
              f"the five largest pages hold {c['share_of_characters_in_largest_5']:.0%} of crawled characters.",
              "", "## E5, re-appended system prompts", "",
              f"System messages hold {res['system_prompt']['mean']:.0%} of researcher-request characters on average "
              f"(range {res['system_prompt']['range'][0]:.0%}–{res['system_prompt']['range'][1]:.0%}). This is a character share.",
              "", "## K2, the reporter's view of the query", "",
              "| Run | Query words restated in title and thought | Thought opens 'The user is asking' |", "|---|---|---|"]
    lines += [f"| {x['run_id']} | {x['query_words_restated']:.0%} | {x['thought_opens_with_user_request']} |"
              for x in res["reporter_requirements"]["rows"]]
    ci, sc = res["citations"], res["step_costs"]
    lines += ["", "## Citations and search", "",
              f"{ci['from_crawls']} of {ci['citations']} reporter citations are crawled URLs; DuckDuckGo hits never become citations.",
              "", "## Cost of a later research step", "",
              "| Later steps | n | Median model calls | Median prompt tokens | Median model seconds |", "|---|---|---|---|---|"]
    lines += [f"| {k.replace('_', ' ')} | {x['steps']} | {x['median_calls']:g} | {x['median_prompt_tokens']:,.0f} | {x['median_wall_s']:g} |"
              for k, x in sc.items()]
    lines += ["", "## Pilot insertion positions", "", "| Case | Arm | Observation | After the step's References list |", "|---|---|---|---|"]
    lines += [f"| {x['case']} | {x['arm']} | {x['observation']} of {x['observations']} | {x['after_references_list']} |"
              for x in res["insertions"]]
    pr = res["probabilities"]
    lines += ["", "## Chance probabilities (independent draws assumed; illustrative, not p-values)", "",
              "| Uptake p in L and B | c05 'ledger uptake', original rule | c05 'ledger uptake', A1 rule |", "|---|---|---|"]
    lines += [f"| {p} | {x['original_rule']:.3f} | {x['a1_rule']:.3f} |" for p, x in pr["c05_uptake_by_chance_no_ledger_effect"].items()]
    lines += ["", "| True per-sample uptake under raw append | P(H1b fails by its rule) |", "|---|---|"]
    lines += [f"| {p} | {x:.3f} |" for p, x in pr["h1b_fails_at_true_uptake"].items()]
    lines += ["", "| Fisher exact test, one-sided | p |", "|---|---|"] + [f"| {k} | {x:.3f} |" for k, x in pr["fisher_one_sided"].items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    runs = completed_runs()
    res = {"relay": relay(runs), "report_numbers": report_numbers(runs), "crawl": crawl(runs), "system_prompt": system_prompt_share(runs),
           "reporter_requirements": reporter_requirements(runs), "citations": citations(runs),
           "step_costs": step_costs(runs), "insertions": insertion_positions(), "probabilities": probabilities()}
    (ANALYSIS_DIR / "rechecks.json").write_text(json.dumps(res, indent=1))
    (ANALYSIS_DIR / "rechecks.md").write_text(report(res))
    print(report(res))


if __name__ == "__main__":
    main()
