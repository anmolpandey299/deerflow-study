"""Versioned run manifest: everything needed to identify what produced a run."""

from __future__ import annotations

import importlib.metadata as md
import platform
import subprocess
from pathlib import Path
from typing import Any

import httpx

from .settings import deerflow_dir, sha256_file, sha256_text

MANIFEST_VERSION = 1
PROMPTS = ("coordinator", "planner", "researcher", "analyst", "coder", "reporter",
           "recursion_fallback")
PACKAGES = ("langchain", "langchain-core", "langchain-openai", "langchain-community",
            "langgraph", "openai", "ddgs", "duckduckgo-search", "httpx")


def _git(ddir: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(ddir), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


def deerflow_info(cfg: dict[str, Any]) -> dict[str, Any]:
    ddir = deerflow_dir(cfg)
    head = _git(ddir, "rev-parse", "HEAD")
    if head != cfg["deerflow"]["commit"]:
        raise RuntimeError(f"DeerFlow checkout is at {head}, config pins {cfg['deerflow']['commit']}")
    return {
        "repo": cfg["deerflow"]["repo"], "branch": cfg["deerflow"]["branch"], "commit": head,
        # empty means no tracked file differs from the pinned commit
        "git_status_porcelain": _git(ddir, "status", "--porcelain"),
        "prompt_sha256": {p: sha256_file(ddir / "src" / "prompts" / f"{p}.md") for p in PROMPTS},
        "graph_sha256": {f: sha256_file(ddir / "src" / "graph" / f) for f in ("builder.py", "nodes.py")},
    }


def ollama_info(base_url: str, tag: str) -> dict[str, Any]:
    root = base_url.rsplit("/v1", 1)[0]
    try:
        version = httpx.get(f"{root}/api/version", timeout=10).json().get("version")
        tags = httpx.get(f"{root}/api/tags", timeout=10).json().get("models", [])
        show = httpx.post(f"{root}/api/show", json={"model": tag}, timeout=30).json()
    except Exception as exc:  # recorded, not fatal: the run itself will fail loudly
        return {"error": repr(exc)}
    digest = next((m.get("digest") for m in tags if m.get("name") in (tag, f"{tag}:latest")), None)
    return {
        "ollama_version": version, "tag": tag, "digest": digest,
        "parameters": show.get("parameters"), "details": show.get("details"),
        "modelfile_sha256": sha256_text(show.get("modelfile", "")),
    }


def package_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for p in PACKAGES:
        try:
            out[p] = md.version(p)
        except md.PackageNotFoundError:
            out[p] = None
    return out


def build(cfg: dict[str, Any], *, conf_yaml: str, probe_code_sha256: dict[str, str],
          **fields: Any) -> dict[str, Any]:
    """probe_code_sha256 must be taken when the run starts (the code actually loaded)."""
    return {
        "manifest_version": MANIFEST_VERSION,
        "experiment_id": cfg["experiment_id"],
        **fields,
        "deerflow": deerflow_info(cfg),
        "config": cfg,
        "deerflow_conf_yaml": conf_yaml,  # contains no secret (Ollama ignores api_key)
        "model": ollama_info(cfg["model"]["base_url"], cfg["model"]["served_tag"]),
        "packages": package_versions(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "probe_code_sha256": probe_code_sha256,
    }
