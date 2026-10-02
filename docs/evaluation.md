# Reproducible evaluation and validation

Run from the repository root:

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s examples/demo_repo -v
python examples/evaluate.py
python -m compileall -q quickcontext tests
```

## Observed locally: 2026-10-02, Linux, Python 3.12.14

- Core regression tests: **33 passed**
- Demo behavior tests: **2 passed**
- `compileall`: passed
- Wheel build and installation into an isolated target: passed
- Installed `qcb` entry point, run outside the source directory: returned expected context and valid JSON
- Additional JSON/Markdown budget stress check: 13 successful packs respected 600–10,000 byte limits; smaller metadata-only limits failed explicitly as expected
- GitHub Actions matrix is configured for Python 3.10, 3.12 and 3.13. Local execution does not establish a remote CI result or validate the other Python versions.

Tests cover incremental reuse/deletion, AST relationships, test discovery, exact byte accounting, Unicode, truncation line ranges, source changes during retrieval, malformed/tampered cache recovery, secret/private-key/binary exclusions, symlinks, ignore behavior, resolved-case validation, Git history opt-in, package CLI and bad-input errors.

## Small synthetic ablation

`examples/evaluate.py` copies the original five-file example to a temporary directory. It queries `checkout_total`, using no imported history, and compares graph expansion with the same lexical pipeline. Labels are only used after retrieval for scoring.

| Mode | Relevant paths found | Output bytes | Heuristic tokens | Model calls |
|---|---:|---:|---:|---:|
| Lexical only | 2/3 | 1,914 | 957 | 0 |
| Lexical + graph | 3/3 | 2,811 | 1,406 | 0 |

Expected paths: `checkout.py`, `billing.py`, `test_checkout.py`. Both modes find the checkout and its test. Graph expansion additionally finds the `apply_discount` implementation in `billing.py`, without the query term being present in that file. The graph result costs more bytes because it includes additional relevant evidence. It is **not** a token-savings or bug-fix-success benchmark.

Cold indexing parsed five files. The immediately repeated refresh reused five records and parsed zero. In one run the measured times were 5.46 ms cold / 9.08 ms warm; those tiny timing samples are dominated by noise and process/filesystem overhead, so no latency speedup is claimed. The reliable incremental observation is avoided reparsing.

A separate historical navigation demo intentionally matches the imported synthetic “Penny mismatch after a promotion” case. It tests use of historical hints and current paths, not held-out generalization. It is excluded from the ablation above. No real-world solved issue, answer patch, private repository, private account data or private source was used in the fixture.

See [the actual Markdown demo output](example-context.md). It was generated from a temporary, unversioned copy of the fixture; a real Git checkout instead reports its HEAD and tracked dirty state. Output metadata, timings and hashes can vary after source changes.

## What this does not establish

There is no statistically meaningful real-world retrieval benchmark, external CodeGraph comparison, model-specific token count, model-generated patch evaluation, large-repository scaling result, or guaranteed secret removal in v0.1. These require separate datasets and measurement. The synthetic fixture demonstrates the mechanism, and the automated suite guards its stated invariants.
