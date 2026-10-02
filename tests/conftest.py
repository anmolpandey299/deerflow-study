import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from boundary_probe import deerflow_env  # noqa: E402
from boundary_probe.settings import RUNS_DIR, deerflow_dir, load_config  # noqa: E402


@pytest.fixture(scope="session")
def cfg():
    config = load_config()
    if not (deerflow_dir(config) / "src").is_dir():
        pytest.skip("needs the pinned DeerFlow checkout in vendor/deer-flow-1x (see README)")
    deerflow_env.prepare(config)  # puts the pinned DeerFlow checkout on sys.path
    return config


def completed_runs():
    """Real recorded runs (used by tests that are skipped when none exist)."""
    out = []
    for d in sorted(RUNS_DIR.glob("*/raw/manifest.json")):
        run_dir = d.parent.parent
        if (run_dir / "EXCLUDED.txt").exists():
            continue
        import json
        if json.loads(d.read_text()).get("status") == "completed":
            out.append(run_dir)
    return out
