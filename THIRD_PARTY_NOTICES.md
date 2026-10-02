# Third-party notices

This repository does not include DeerFlow source code. Its recorded runs and replays (`runs/`, `analysis/`, `part2_pilot/outputs/`) contain prompt text rendered from DeerFlow templates at commit `2ab28765803d4d9582aaa8f2f3355137d154e273`, which is distributed under the following licence.

```text
MIT License

Copyright (c) 2025 Bytedance Ltd. and/or its affiliates

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The same records also contain:

- outputs of the models `qwen3:4b-instruct-2507-q4_K_M` (agent) and `gpt-oss:20b` (proxy judge), served locally by Ollama;
- text from public web pages returned by DuckDuckGo search and the Jina reader, kept verbatim as research records. Most of it is short excerpts; `runs/*/raw/crawl_fulltext.jsonl` holds the full fetched text of crawled pages. Copyright in that text remains with its owners. Some of it includes contact e-mail addresses printed on the source pages.
