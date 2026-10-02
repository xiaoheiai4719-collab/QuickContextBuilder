"""Reproduce a synthetic held-out-query ablation. No LLM, no fix success claims."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quickcontext import Builder


def run():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        shutil.copytree(Path(__file__).parent / "demo_repo", root,
                        ignore=shutil.ignore_patterns(".qcb", "__pycache__"))
        builder = Builder(root)
        started = perf_counter()
        cold = builder.refresh()
        cold_ms = (perf_counter() - started) * 1000
        started = perf_counter()
        warm = builder.refresh()
        warm_ms = (perf_counter() - started) * 1000
        query = "checkout_total"
        expected = {"checkout.py", "billing.py", "test_checkout.py"}
        results = []
        # No history is imported for this ablation. Expected paths are evaluation
        # labels only; they are never given to the retriever.
        for graph in (False, True):
            pack, output = builder.build(query, graph=graph, format="json", token_budget=4000)
            paths = {s["path"] for s in pack["snippets"]}
            results.append({"mode": "lexical+graph" if graph else "lexical", "query": query,
                            "selected_paths": sorted(paths), "expected_path_recall": len(paths & expected) / len(expected),
                            "output_bytes": len(output.encode()), "estimated_tokens": pack["budget"]["estimated_tokens"],
                            "model_calls": 0, "history_enabled": False})
        # Separate historical navigation demonstration, not a held-out benchmark.
        builder.import_cases(Path(__file__).parent / "resolved_cases.json")
        historical, _ = builder.build("Penny mismatch after a promotion", token_budget=4000)
        report = {"dataset": "original synthetic 5-file fixture; not a real-world benchmark",
                  "expected_paths": sorted(expected), "cold_index": cold, "warm_index": warm,
                  "cold_ms": round(cold_ms, 2), "warm_ms": round(warm_ms, 2), "ablation": results,
                  "history_navigation_demo": {"query": "Penny mismatch after a promotion",
                      "selected_paths": sorted({s["path"] for s in historical["snippets"]}),
                      "warning": "This deliberately matches the supplied historical case; not a held-out quality result."}}
        assert results[0]["expected_path_recall"] < results[1]["expected_path_recall"]
        assert results[1]["expected_path_recall"] == 1
        assert cold["parsed"] == 5 and warm["reused"] == 5
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
