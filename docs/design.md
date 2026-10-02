# Design notes

## Pipeline

1. Discover allowed local UTF-8 files. Git supplies tracked plus non-ignored untracked paths when available. Always apply additional exclusions and reject symlinks.
2. Hash bytes with SHA-256. Reuse structurally valid cached records only when content hashes match and cached snippet text matches redacted current lines. Reparse changed files with Python AST or plain text windows. Writes to `.qcb/index.json` are atomic.
3. Split the question and documents into identifier-aware terms. Compute BM25-style scores; boost explicit paths and paths from relevant historical cases. Stopwords and a small CJK bigram tokenizer help lexical matching, without semantic translation.
4. Resolve Python imports/local direct calls when names and local modules permit. Expand one hop in both directions from at most eight positive-score seeds. Treat all edges as candidates because static name resolution is limited. Related tests get a small bonus only after relevant query/graph/history evidence.
5. Sort deterministically by score and chunk ID. Greedily pack source chunks; shrink an oversized chunk around its best query-matching line. Historical metadata has a small allowance so it cannot dominate the pack. Include edges only when both indexed chunks were selected and space remains.
6. Serialize repeatedly until self-reported byte/estimate counts stabilize. Check the whole serialized result against the hard byte limit. Re-read selected files, verify hashes, and compare every displayed snippet to the current redacted source lines. Fail if a selected file changed during retrieval.

The cache stores redacted excerpts and AST metadata; it is not an encrypted database. AST extraction occurs on redacted text, so redaction may invalidate parsing and cause a safe plain-text fallback. The cache is not cryptographically authenticated: malformed/content-altered entries are rebuilt, but a hostile local user can manipulate ranking or graph metadata. Do not accept caches from untrusted parties. Delete `.qcb/index.json` to rebuild; this leaves imported cases intact.

## Provenance

JSON packs expose schema version, requested question, Git HEAD if available, tracked-dirty state, indexing statistics, budget accounting, history references, snippets, and selected relationships. Every snippet has repository-relative path, inclusive line range, original indexed chunk ID, full current-file SHA-256, symbol/kind, text, score, reasons and truncation status. A truncated snippet retains the original chunk ID so relationships remain interpretable; its displayed line interval is authoritative. An edge can originate outside the displayed truncated window.

HEAD is repository metadata, not a claim that every snippet is committed. Untracked files can be included, and `tracked_dirty` excludes them. File SHA-256 identifies the current bytes. Selected files are rechecked before output, but the program cannot lock your editor or promise a repository-wide atomic snapshot. Rebuild if the checkout changes.

## Cost and scaling

There are zero model calls and no embedding/model downloads. Hashing reads eligible files on each refresh; unchanged files avoid AST reparsing. Retrieval recomputes document term counts and graph candidates in memory. JSON cache rewrites are proportional to index size. This prioritizes portability and correctness over huge-repository throughput. Byte savings compared with sending an entire repository vary by task; no blanket savings claim is made.

The token estimate is a heuristic (`ceil(UTF-8 bytes / 2)`), not an exact tokenizer and not an upper bound on model tokens. Very small budgets can leave no fitting source. Query/file-count caps and richer retrieval backends can be future work; a caller analyzing hostile or enormous input should impose process memory/time limits.

## History design

Import is explicit and replaces all previously imported case records. Required fields are validated; traversal/absolute paths and unresolved cases are rejected. Summaries are used only for ranking. Existing paths are re-resolved against the current allowed index. Old patches/source never override current code. Git history is separately opt-in and imports only subjects and changed filenames, not authors, emails, commit bodies or patch bodies. Git commit subjects are not evidence of successful resolution.

## Boundaries and next steps

This MVP has no full type system, dynamic dispatch analysis, embedding search, automatic repository modification, model integration or issue fetching. Natural-language semantic mismatches can return nothing. The first useful next steps are a pinned/versioned external graph adapter with stale-source validation, optional model-specific tokenizers, real held-out issue evaluation against lexical and file-search baselines, and a more scalable index. These are proposals, not implemented features.
