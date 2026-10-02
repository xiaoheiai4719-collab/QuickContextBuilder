# QuickContextBuilder

**Turn a coding question into a small, traceable pack of current source, relationship candidates, and relevant tests.** Offline. No model key. Zero runtime dependencies. Python 3.10+.

AI coding assistants often spend context discovering files before doing useful work. QuickContextBuilder moves that first pass into a local, deterministic CLI: rank by the question, follow a few code relationships, use past incidents as navigation hints, then fit the result into a stated budget.

This is a working **v0.1 Python-first MVP**, not a full semantic code intelligence engine. [Design and limitations](docs/design.md) · [CodeGraph research](docs/codegraph-research.md) · [Security](SECURITY.md)

## Try it in a minute

```bash
git clone https://github.com/xiaoheiai4719-collab/QuickContextBuilder.git
cd QuickContextBuilder

# No installation needed
python -m quickcontext build examples/demo_repo \
  --query "checkout_total" --token-budget 1800

# Optional: install the qcb command (setuptools is a build-time dependency)
python -m pip install -e .
qcb build /path/to/your/repo -q "Where is authenticate normalized?" \
  --token-budget 3000 --max-bytes 6000 --output /tmp/context.md
```

The demo follows `checkout_total` to `apply_discount` in `billing.py`, even though that file does not contain the queried identifier. It also finds `test_checkout.py`. Every displayed snippet has line numbers, the current file's SHA-256, a relevance score, selection reasons, and an explicit truncation flag.

Sample excerpt (the real output includes hashes and accounting):

```text
## billing.py:10-11 (apply_discount)
Reasons: static-call-candidate:checkout.py:4-7
   10 | def apply_discount(amount, percent):
   11 |     return round_amount(Decimal(str(amount)) * (1 - Decimal(str(percent)) / 100))
```

Save the output outside the repository you are indexing, or exclude it with `.qcbignore`, to avoid feeding an earlier pack into a later search. Review a pack before sending it to any model. The tool itself makes no network/model calls and does not send your code anywhere.

## What ships

- **Question-driven retrieval:** BM25-style lexical ranking, snake/camel identifier splitting, exact-path boosts, and limited CJK lexical matching
- **Python structure:** standard-library AST chunks with module-level functions/classes, resolvable imports and direct call candidates; one-hop caller/callee expansion from the top eight seeds
- **Related tests:** discover test files via query/relationship evidence and a small ranking boost, without running repository code
- **Fresh source:** SHA-256 incremental indexing; changed files reparse, deleted files disappear; selected snippets and hashes are rechecked before returning
- **Bounded output:** complete Markdown or JSON, including metadata, fits a hard UTF-8 byte cap; oversized snippets become truthful contiguous line windows
- **Historical hints:** explicitly import resolved issue summaries or opt into recent local commit subjects/changed paths; always retrieve present-day source
- **Local by default:** `.gitignore` handling through Git, additional `.qcbignore`, protected-path exclusions, no symlink traversal, credential-pattern redaction

## Budget semantics: read this first

`--token-budget N` limits **our heuristic estimate**, `ceil(UTF-8 output bytes / 2)`, to N. It is not a model tokenizer and **is not an upper bound on actual model tokens**. Code, languages, random strings, and tokenizer families have different ratios. No token-savings percentage or dollar savings is claimed.

The exact guarantee is `output_bytes <= min(2 * token_budget, max_bytes)` when `--max-bytes` is supplied; otherwise `output_bytes <= 2 * token_budget`. Counts cover the entire serialized output, including its final newline. If even metadata cannot fit, the command fails with exit code 2. To enforce a specific model's context limit, run that model's tokenizer downstream and reserve room for your other prompt content.

## Usage

```bash
# Optional warm-up. Every build refreshes automatically.
qcb index /path/to/repo

# A question in a local UTF-8 file; deterministic structured output
qcb build /path/to/repo --query-file issue.txt --format json --token-budget 4000

# Opt in to the most recent 50 LOCAL commits. No remote issue fetching.
qcb build /path/to/repo -q "retry timeout regression" --git-history 50

# Compare against the same lexical pipeline with graph expansion disabled
qcb build examples/demo_repo -q checkout_total --no-graph

# Import an explicit, reviewed set of resolved incidents. Replaces prior imported cases.
qcb import-cases examples/demo_repo examples/resolved_cases.json
qcb build examples/demo_repo -q "Penny mismatch after a promotion"
```

A resolved case is a navigation record, not an old patch to paste into the prompt:

```json
[
  {
    "id": "issue-42",
    "resolved": true,
    "title": "Penny mismatch after a promotion",
    "summary": "The prior incident was localized to currency handling.",
    "files": ["billing.py", "test_billing.py"],
    "source": "https://example.invalid/issues/42"
  }
]
```

Summaries influence ranking but are not emitted. Output includes the matched case ID, title, source, and only currently indexed file paths. Removed/ignored paths cannot pull old source into a pack. Imported resolution status is a user assertion; commit messages alone never imply an issue is solved. Raw patches and historical source are not imported in v0.1. You can prepare this small schema from your own solved-issue/patch records after review.

### Python API

```python
from quickcontext import Builder

pack, markdown = Builder("/path/to/repo").build(
    "authenticate", token_budget=3000, max_bytes=6000
)
print(markdown, end="")
print(pack["budget"])
```

### Extra exclusions

Create `.qcbignore` at the analyzed repository root:

```gitignore
private/
*.generated.py
reports/
```

It is deliberately exclusion-only (no `!` re-inclusion). In a Git checkout, Git determines tracked and non-ignored untracked files. Tracked files remain eligible even when matched by `.gitignore`; protected defaults and `.qcbignore` still apply. Without Git, only simple root `.gitignore` patterns are supported. Add `.qcb/` to your own repository's `.gitignore`: its local cache contains source excerpts and case hints and must not be committed.

## Languages and limits

Python gets AST structure. JavaScript/TypeScript, Java, Go, Rust, C/C++, C#, Ruby, PHP, Swift, Kotlin, Scala, SQL, shell, common docs/config text get lexical 60-line windows only. This release does **not** claim semantic graphs for those languages. UTF-8 files only, maximum 512 KB per file; binary, credential/private-key files and selected generated/dependency paths are skipped.

Python graph edges are candidates, not runtime truth: dynamic dispatch, re-exports, decorators, aliases/shadowing, nested definitions, complex package roots and cross-language calls can be missed or misresolved. One-hop expansion can miss deeper callees. No embeddings, language translation, MCP server, external CodeGraph adapter, issue API, or automatic bug fixing ships yet. JSON caching and full-scan lexical retrieval target small-to-medium repositories; this is not a million-file index.

## Reproduce the checks

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s examples/demo_repo -v
python examples/evaluate.py
python -m compileall -q quickcontext tests
```

The small **synthetic** ablation queries `checkout_total` with no history imported. Lexical-only retrieval finds 2/3 labeled relevant paths; enabling the graph finds 3/3, adding `billing.py`. It uses zero model calls. The graph output is larger because it brings needed context; this is a coverage example, not evidence of token savings, real-world accuracy, or patch success. Labels are never passed to the retriever. The separate historical case demonstration is clearly marked and is not a held-out benchmark. [Measured example](docs/evaluation.md)

## 中文快速开始

这是一个可离线运行的“按问题构建代码上下文”首版工具：输入问题 → 搜索代码 → 补充 Python 调用/导入关系和相关测试 → 在预算内输出当前源码片段。无需 API Key，不调用大模型。

```bash
python -m quickcontext build /你的仓库路径 \
  --query "checkout_total 为什么金额不对" \
  --token-budget 3000 --max-bytes 6000 --output /tmp/context.md
```

最好在问题中带上错误信息、函数名或路径。中文支持词法匹配，但不会自动把中文问题翻译成英文代码语义。`--token-budget` 是启发式估算限制，不是模型精确 token 上限；完整输出的字节上限是硬约束。历史案例只帮助定位，最终代码从当前工作区读取并校验哈希。默认忽略部分敏感文件并做有限脱敏，但分享前仍需人工检查。

## License and contribution

Original implementation and original demo fixtures: [MIT](LICENSE). No third-party CodeGraph source is vendored. Runtime uses only the Python standard library; Git is optional for ignore fidelity, revision metadata and local history. Packaging uses setuptools; CI uses official GitHub Actions. See [CONTRIBUTING.md](CONTRIBUTING.md).
