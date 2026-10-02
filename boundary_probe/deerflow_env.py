"""Runtime hooks into the pinned DeerFlow 1.x checkout.

No vendor file is edited. The hooks are:
  1. conf.yaml (git-ignored in DeerFlow) written from experiments/config.yaml;
  2. the recording (or replay) model placed in src.llms.llm._llm_cache["basic"],
     which get_llm_by_type() returns for every role (AGENT_LLM_MAP is all "basic");
  3. web_search / crawl_tool rebound in src.graph.nodes to cassette proxies;
  4. the prompt clock (CURRENT_TIME) frozen for the whole run so that a recorded
     run can be replayed byte-for-byte;
  5. a side-channel log of crawled pages *before* DeerFlow's 1,000-char cut.
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
import time
from typing import Any

import yaml

from .cassette import Cassette, CassetteTool
from .recording import CallLog, RecordingChatOpenAI
from .settings import deerflow_dir

# DeerFlow's Configuration.from_runnable_config() lets environment variables with
# these names silently override the per-run config; refuse to run if any is set.
_OVERRIDE_ENV = (
    "RESOURCES", "MAX_PLAN_ITERATIONS", "MAX_STEP_NUM", "MAX_SEARCH_RESULTS",
    "MCP_SETTINGS", "REPORT_STYLE", "ENABLE_DEEP_THINKING", "ENFORCE_WEB_SEARCH",
    "ENFORCE_RESEARCHER_SEARCH", "ENABLE_WEB_SEARCH", "INTERRUPT_BEFORE_TOOLS",
    "ENABLE_RECURSION_FALLBACK", "AGENT_RECURSION_LIMIT",
)


def conf_yaml_text(cfg: dict[str, Any]) -> str:
    m = cfg["model"]
    conf = {"BASIC_MODEL": {
        "base_url": m["base_url"], "model": m["served_tag"], "api_key": "ollama",
        "temperature": m["temperature"], "top_p": m["top_p"], "seed": m["seed"],
        "max_tokens": m["max_tokens"], "token_limit": m["token_limit"],
    }}
    return yaml.safe_dump(conf, sort_keys=True)


def prepare(cfg: dict[str, Any]) -> str:
    """Call before importing any DeerFlow `src.*` module. Returns conf.yaml text."""
    bad = [k for k in _OVERRIDE_ENV if k in os.environ]
    if bad:
        raise RuntimeError(f"environment overrides DeerFlow run config: {bad}")
    ddir = deerflow_dir(cfg)
    os.chdir(ddir)  # some DeerFlow config reads use a CWD-relative "conf.yaml"
    if str(ddir) not in sys.path:
        sys.path.insert(0, str(ddir))
    os.environ["SEARCH_API"] = cfg["tools"]["search_api"]  # read at import time
    text = conf_yaml_text(cfg)
    (ddir / "conf.yaml").write_text(text)
    return text


def model_kwargs(cfg: dict[str, Any]) -> dict[str, Any]:
    """Same parameters DeerFlow's _create_llm_use_conf would pass to ChatOpenAI."""
    m = cfg["model"]
    return dict(
        model=m["served_tag"], base_url=m["base_url"], api_key="ollama",
        temperature=m["temperature"], top_p=m["top_p"], seed=m["seed"],
        max_tokens=m["max_tokens"], max_retries=3,
        disable_streaming=True,  # one request per call, so capture is exact
    )


def inject_model(model) -> None:
    import src.llms.llm as llm_mod

    llm_mod._llm_cache.clear()
    llm_mod._llm_cache["basic"] = model


def freeze_prompt_time(frozen: _dt.datetime) -> None:
    import src.prompts.template as template_mod

    class _FrozenDatetime(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen if tz is None else frozen.astimezone(tz)

    template_mod.datetime = _FrozenDatetime


def install_tools(cassette: Cassette, crawl_log: list | None = None,
                  search_factory=None, crawl_inner=None) -> None:
    """search_factory / crawl_inner replace DeerFlow's live tools (tests only)."""
    import src.graph.nodes as nodes
    import src.tools.crawl as crawl_mod
    import src.tools.search as search_mod

    original_get_search = search_factory or search_mod.get_web_search_tool
    original_crawl = crawl_inner or crawl_mod.crawl_tool

    def get_web_search_tool(max_search_results: int):
        return CassetteTool(original_get_search(max_search_results), cassette)

    nodes.get_web_search_tool = get_web_search_tool
    nodes.crawl_tool = CassetteTool(original_crawl, cassette)

    _crawl_log_target[0] = crawl_log
    if not getattr(crawl_mod.compress_crawl_content, "_probe", False):
        original_compress = crawl_mod.compress_crawl_content

        def compress_crawl_content(article):
            shown = original_compress(article)  # DeerFlow's own truncation, unchanged
            target = _crawl_log_target[0]
            if target is not None:
                full = article.to_markdown()
                target.append({"url": getattr(article, "url", None), "t": time.time(),
                               "full_chars": len(full), "shown_chars": len(shown),
                               "full_markdown": full})
            return shown

        compress_crawl_content._probe = True
        crawl_mod.compress_crawl_content = compress_crawl_content


_crawl_log_target: list = [None]


def recording_model(cfg: dict[str, Any], call_log: CallLog) -> RecordingChatOpenAI:
    return RecordingChatOpenAI(call_log=call_log, **model_kwargs(cfg))
