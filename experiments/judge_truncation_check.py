"""Does the in-repo judge's request path truncate long prompts? (protocol A12)

    vendor/deer-flow-1x/.venv/bin/python experiments/judge_truncation_check.py

DeerFlow's LLMJudge is driven through Ollama's OpenAI-compatible endpoint
(/v1/chat/completions), which does not accept num_ctx. This sends the same ~7.5k-token
needle prompt as ollama_truncation_check.py through that endpoint to (a) gpt-oss:20b,
which uses the server default context, and (b) the derived tag with num_ctx 32768.
Writes analysis/judge_truncation_check.json.
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
for tag in ("gpt-oss:20b", "dfprobe-gptoss-20b-ctx32k"):
    r = httpx.post("http://localhost:11434/v1/chat/completions", timeout=900, json={
        "model": tag, "messages": messages, "temperature": 0, "seed": 1, "max_tokens": 2000}).json()
    answer = r["choices"][0]["message"]["content"] or ""
    rows.append({"tag": tag, "endpoint": "/v1/chat/completions",
                 "prompt_tokens": r["usage"]["prompt_tokens"], "answer": answer[:200],
                 "needle_recovered": "7319-ALPHA" in answer})
    print(rows[-1])
(ROOT / "analysis" / "judge_truncation_check.json").write_text(json.dumps(rows, indent=1))
