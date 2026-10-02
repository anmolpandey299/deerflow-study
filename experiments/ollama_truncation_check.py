"""Does Ollama silently truncate long prompts at its default context length?

    vendor/deer-flow-1x/.venv/bin/python experiments/ollama_truncation_check.py

Sends the same ~6k-token prompt (a "needle" at the very start, the question at the
end) to (a) the base tag, which uses the server default context, and (b) the pinned
40k-context tag used in every run. Records prompt_eval_count and the answer.
Writes analysis/ollama_truncation_check.json.
"""

import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
filler = " ".join(f"Paragraph {i}: the committee reviewed routine logistics and scheduling matters "
                  f"without notable outcomes." for i in range(420))
messages = [{"role": "system", "content": "SECRET CODE: the vault code is 7319-ALPHA. Remember it."},
            {"role": "user", "content": filler + "\n\nQuestion: what is the vault code stated in the "
                                                 "system message? Answer with the code only."}]
rows = []
for tag in ("qwen3:4b-instruct-2507-q4_K_M", "dfprobe-qwen3-4b-ctx40k"):
    r = httpx.post("http://localhost:11434/api/chat", timeout=900, json={
        "model": tag, "messages": messages, "stream": False,
        "options": {"temperature": 0, "seed": 1, "num_predict": 20}}).json()
    rows.append({"tag": tag, "prompt_eval_count": r.get("prompt_eval_count"),
                 "answer": r["message"]["content"], "needle_recovered": "7319-ALPHA" in r["message"]["content"]})
    print(rows[-1])
(ROOT / "analysis" / "ollama_truncation_check.json").write_text(json.dumps(rows, indent=1))
