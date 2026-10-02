"""Paths, pinned configuration, and small hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "experiments" / "config.yaml"
QUERIES_PATH = ROOT / "experiments" / "dev_queries.yaml"
RUNS_DIR = ROOT / "runs"
ANALYSIS_DIR = ROOT / "analysis"


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text())


def deerflow_dir(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config()
    return ROOT / cfg["deerflow"]["path"]


def load_queries() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(QUERIES_PATH.read_text())
    return {q["id"]: q for q in data["queries"]}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_json(obj: Any) -> str:
    """Stable serialisation used for cache keys and request hashing."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def code_fingerprint() -> dict[str, str]:
    """SHA-256 of every source file of this package (stands in for a commit id)."""
    pkg = ROOT / "boundary_probe"
    return {p.name: sha256_file(p) for p in sorted(pkg.glob("*.py"))}
