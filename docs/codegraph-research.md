# Which CodeGraph? Research and decision

Reviewed public primary repository pages on **2026-10-02**. “CodeGraph” is not a unique project name. This first release does not claim integration with any of the following, and includes none of their source code.

| Project | Relevant advertised capabilities | License evidence | Decision for v0.1 |
|---|---|---|---|
| [CodeGraphContext/CodeGraphContext](https://github.com/CodeGraphContext/CodeGraphContext) | CLI/MCP and multi-language source graphs, graph database and symbol relationships | [LICENSE](https://github.com/CodeGraphContext/CodeGraphContext/blob/main/LICENSE) is MIT | Strong candidate for a future optional graph adapter. A graph runtime/parser dependency is unnecessary for the small standard-library MVP. |
| [codegraph-ai/CodeGraph](https://github.com/codegraph-ai/CodeGraph) | Rust-based multi-language graph engine, MCP/LSP, persistent storage; README documents a graph-only mode | Repository README/license indicator says Apache-2.0; [LICENSE link](https://github.com/codegraph-ai/CodeGraph/blob/main/LICENSE) returned an HTTP error during this review | Consider an out-of-process adapter after pinning and verifying the exact release/license. Not vendored or executed here. |
| [gitstq/codegraph](https://github.com/gitstq/codegraph) | Python local graph CLI, incremental indexing and context/export commands | Repository README includes the MIT license; direct LICENSE retrieval failed during this review | Closest lightweight design reference, but no stable export adapter was verified. Our code is original; its savings claims are not adopted. |
| [isink17/codegraph](https://github.com/isink17/codegraph) | Go/tree-sitter/SQLite, task context, related tests and MCP | [LICENSE](https://github.com/isink17/codegraph/blob/master/LICENSE) specifies FSL 1.1, a commercial-product restriction, and future Apache-2.0 on 2028-03-18; README describes a different future-license variant | Not selected. Do not treat this as currently MIT or copy it into this MIT project. The upstream README/LICENSE discrepancy must be resolved before reuse. |

## Why not force an integration now?

The desired outcome is a question-specific, low-cost, traceable context pack. A graph engine supplies one ingredient; it does not remove the need to budget the final prompt, rank question relevance, treat old fixes cautiously, validate current file content, and expose limitations.

Version 0.1 therefore implements a small original Python AST relationship layer. This keeps the default fully offline, installation-light and independently testable. It deliberately gives up richer multi-language semantic resolution. Non-Python files still work through lexical text retrieval.

A future CodeGraphContext adapter is the leading option based on its documented interface and directly inspected MIT license. It should be optional, pin a supported upstream version/schema, normalize paths and source ranges, label relation confidence, and reject stale content against the current checkout. None of that adapter exists in this release. Selecting a candidate is not a claim of compatibility or endorsement.

No upstream performance claims were independently reproduced. Primary README descriptions above are used to explain the design decision, not benchmark this project.
