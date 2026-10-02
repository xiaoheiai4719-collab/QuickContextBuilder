import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from quickcontext import Builder, ContextError, estimate_tokens
from quickcontext.cli import main
from quickcontext.core import allowed, parse_file, redact, safe_relative, terms


class RepoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.builder = Builder(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def demo(self):
        self.put("maths.py", "def normalize(value):\n    return value.strip().lower()\n")
        self.put("service.py", "from maths import normalize\n\ndef authenticate(username):\n    return normalize(username)\n")
        self.put("test_service.py", "from service import authenticate\n\ndef test_login():\n    assert authenticate(' A ') == 'a'\n")
        self.put("unrelated.py", "def banana():\n    return 17\n")

    def test_incremental_refresh(self):
        self.demo()
        first = self.builder.refresh()
        self.assertEqual(first["parsed"], 4)
        self.assertEqual(self.builder.refresh()["reused"], 4)
        self.put("maths.py", "def normalize(value):\n    return str(value).lower()\n")
        self.assertEqual(self.builder.refresh()["parsed"], 1)
        (self.root / "unrelated.py").unlink()
        self.assertEqual(self.builder.refresh()["deleted"], 1)

    def test_graph_reaches_callee_and_test(self):
        self.demo()
        pack, _ = self.builder.build("authenticate", token_budget=5000, format="json")
        paths = {c["path"] for c in pack["snippets"]}
        self.assertIn("maths.py", paths)
        self.assertIn("test_service.py", paths)
        self.assertNotIn("unrelated.py", paths)
        self.assertTrue(any(e["kind"] == "static-call-candidate" for e in pack["edges"]))
        lexical, _ = self.builder.build("authenticate", token_budget=5000, graph=False)
        self.assertNotIn("maths.py", {c["path"] for c in lexical["snippets"]})

    def test_every_serialized_budget_is_hard(self):
        self.demo()
        for fmt in ("json", "markdown"):
            for budget in (450, 700, 1500, 3000):
                pack, output = self.builder.build("authenticate 用户", token_budget=budget, format=fmt)
                self.assertLessEqual(len(output.encode()), budget * 2)
                self.assertEqual(pack["budget"]["output_bytes"], len(output.encode()))
                self.assertEqual(pack["budget"]["estimated_tokens"], estimate_tokens(output))
                self.assertLessEqual(estimate_tokens(output), budget)
        _, output = self.builder.build("authenticate", max_bytes=1400)
        self.assertLessEqual(len(output.encode()), 1400)

    def test_tiny_budget_errors_without_output(self):
        self.demo()
        with self.assertRaises(ContextError):
            self.builder.build("authenticate", token_budget=1)

    def test_source_changes_auto_refresh(self):
        self.demo()
        a, _ = self.builder.build("normalize", token_budget=5000)
        old = next(c for c in a["snippets"] if c["path"] == "maths.py")
        self.put("maths.py", "def normalize(value):\n    return 'brand_new'\n")
        b, _ = self.builder.build("normalize", token_budget=5000)
        new = next(c for c in b["snippets"] if c["path"] == "maths.py")
        self.assertNotEqual(old["sha256"], new["sha256"])
        self.assertIn("brand_new", new["text"])

    def test_change_during_build_fails_closed(self):
        self.demo()
        from quickcontext.core import read_source
        counts = {}
        def changing(root, relative):
            counts[relative] = counts.get(relative, 0) + 1
            raw = read_source(root, relative)
            return b"changed" if counts[relative] > 1 else raw
        with patch("quickcontext.core.read_source", side_effect=changing):
            with self.assertRaisesRegex(ContextError, "Source changed"):
                self.builder.build("authenticate", token_budget=5000)

    def test_secrets_and_binary_are_excluded(self):
        self.put(".env", "API_KEY=private_value")
        self.put("secret_settings.py", "password='really_private'")
        self.put("service.py", "api_key = 'fictional_key_12345'\nprint('hello')\n")
        self.put("key.md", "-----BEGIN PRIVATE KEY-----\nprivate\n")
        (self.root / "binary.py").write_bytes(b"abc\0def")
        self.builder.refresh()
        self.assertEqual(set(self.builder.index["files"]), {"service.py"})
        data = (self.root / ".qcb/index.json").read_text()
        self.assertNotIn("fictional_key_12345", data)
        self.assertIn("REDACTED", data)

    def test_symlink_files_and_dirs_excluded(self):
        self.put("real.py", "print('allowed')")
        (self.root / "link.py").symlink_to(self.root / "real.py")
        (self.root / "linked").symlink_to(self.root, target_is_directory=True)
        self.builder.refresh()
        self.assertEqual(set(self.builder.index["files"]), {"real.py"})

    def test_symlink_cache_refused(self):
        other = self.root / "other"
        other.mkdir()
        (self.root / ".qcb").symlink_to(other, target_is_directory=True)
        with self.assertRaises(ContextError):
            Builder(self.root)

    def test_qcbignore(self):
        self.put(".qcbignore", "private/\n*.generated.py\n")
        self.put("private/a.py", "print('hide')")
        self.put("safe.py", "print('show')")
        self.put("x.generated.py", "print('hide')")
        self.builder.refresh()
        self.assertEqual(set(self.builder.index["files"]), {"safe.py"})

    @unittest.skipUnless(shutil.which("git"), "git unavailable")
    def test_git_ignore_tracked_and_untracked(self):
        self.run_git("init", "-q")
        self.put(".gitignore", "ignored.py\n.qcb/\n")
        self.put("ignored.py", "print('hide')")
        self.put("safe.py", "print('show')")
        self.builder.refresh()
        self.assertEqual(set(self.builder.index["files"]), {"safe.py"})

    def test_case_hints_only_current_paths(self):
        self.put("billing.py", "def amount():\n    return 1\n")
        cases = self.put("cases.input", json.dumps([{"id": "42", "title": "Penny mismatch", "summary": "Historic incident",
                      "resolved": True, "files": ["billing.py", "deleted.py"], "source": "fixture"}]))
        self.assertEqual(self.builder.import_cases(cases), 1)
        pack, output = self.builder.build("Penny mismatch", token_budget=4000)
        self.assertEqual(pack["history"][0]["files"], ["billing.py"])
        self.assertIn("billing.py", {c["path"] for c in pack["snippets"]})
        self.assertNotIn("Historic incident", output)
        self.assertNotIn("deleted.py", output)

    def test_unresolved_and_traversal_cases_rejected(self):
        for values in ({"resolved": False}, {"files": ["../private.py"]}, {"files": "a.py"}, {"files": []}):
            case = {"id": "a", "title": "b", "summary": "c", "files": ["a.py"], "resolved": True, **values}
            file = self.put("cases.input", json.dumps([case]))
            with self.assertRaises(ContextError):
                self.builder.import_cases(file)

    @unittest.skipUnless(shutil.which("git"), "git unavailable")
    def test_git_history_opt_in_and_revision(self):
        self.run_git("init", "-q")
        self.put("logic.py", "def amount():\n    return 1\n")
        self.run_git("add", "logic.py")
        self.run_git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Resolve penny mismatch")
        without, _ = self.builder.build("penny mismatch")
        self.assertFalse(without["history"])
        pack, output = self.builder.build("penny mismatch", git_history=10, token_budget=3000)
        self.assertEqual(len(pack["revision"]), 40)
        self.assertFalse(pack["tracked_dirty"])
        self.assertFalse(pack["history"][0]["resolved"])
        self.assertIn("logic.py", output)
        self.assertNotIn("test@example.invalid", output)

    def test_invalid_python_falls_back(self):
        self.put("bad.py", "def broken(\n    invalid\n")
        self.builder.refresh()
        self.assertEqual(self.builder.index["files"]["bad.py"]["parser"], "text")

    def test_non_python_text(self):
        self.put("service.ts", "export function authenticate(name: string) { return name; }\n")
        pack, _ = self.builder.build("authenticate")
        self.assertEqual(pack["snippets"][0]["path"], "service.ts")
        self.assertEqual(pack["edges"], [])

    def test_unicode(self):
        self.put("用户.py", "def validate():\n    # 用户认证失败\n    return False\n")
        pack, output = self.builder.build("用户认证失败", token_budget=2000)
        self.assertTrue(pack["snippets"])
        self.assertLessEqual(len(output.encode()), 4000)

    def test_long_snippet_is_trimmed_with_true_lines(self):
        content = ["def authenticate(value):"] + [f"    x_{i} = '" + "z" * 35 + "'" for i in range(50)] + ["    return value"]
        self.put("service.py", "\n".join(content))
        pack, _ = self.builder.build("authenticate", token_budget=800)
        self.assertTrue(pack["snippets"])
        for snippet in pack["snippets"]:
            self.assertTrue(snippet["truncated"])
            self.assertEqual(snippet["text"], "\n".join(content[snippet["start"] - 1:snippet["end"]]))

    def test_empty_repo_and_no_matches(self):
        pack, output = self.builder.build("unfindable")
        self.assertEqual(pack["snippets"], [])
        self.assertIn("No source snippets", output)

    def test_cli_stdout_json(self):
        self.demo()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["build", str(self.root), "-q", "authenticate", "--format", "json"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stdout.getvalue())["snippets"])

    def test_cli_query_file_and_output(self):
        self.demo()
        issue = self.put("issue.input", "authenticate")
        output = self.root / "result.output"
        self.assertEqual(main(["build", str(self.root), "--query-file", str(issue), "-o", str(output)]), 0)
        self.assertIn("authenticate", output.read_text())

    def test_cli_bad_budget_returns_two(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["build", str(self.root), "-q", "hello", "--token-budget", "-1"]), 2)

    def test_relative_import_and_module_alias_edges(self):
        self.put("pkg/__init__.py", "")
        self.put("pkg/helpers.py", "def normalize(value):\n    return value\n")
        self.put("pkg/service.py", "from .helpers import normalize as norm\n\ndef authenticate(value):\n    return norm(value)\n")
        self.put("other.py", "import pkg.helpers as h\n\ndef work(value):\n    return h.normalize(value)\n")
        self.builder.refresh()
        edges = self.builder._graph()
        self.assertTrue(any(e["source"].startswith("pkg/service.py:3") and e["target"].startswith("pkg/helpers.py") for e in edges))
        self.assertTrue(any(e["source"].startswith("other.py:3") and e["target"].startswith("pkg/helpers.py") for e in edges))

    def test_oversized_and_non_utf8_skipped(self):
        self.put("huge.py", "x" * 600_000)
        (self.root / "invalid.py").write_bytes(b"\xff\xfe")
        self.assertEqual(self.builder.refresh()["files"], 0)

    def test_cache_corruption_rebuilds(self):
        self.demo()
        self.builder.refresh()
        (self.root / ".qcb/index.json").write_text("bad json")
        self.assertEqual(self.builder.refresh()["parsed"], 4)

    def test_tampered_cache_cannot_inject_source(self):
        self.demo()
        self.builder.refresh()
        path = self.root / ".qcb/index.json"
        data = json.loads(path.read_text())
        data["files"]["maths.py"]["chunks"][0]["text"] = "UNRELATED_INJECTED_TEXT"
        path.write_text(json.dumps(data))
        pack, output = self.builder.build("normalize", token_budget=5000)
        self.assertNotIn("UNRELATED_INJECTED_TEXT", output)
        self.assertEqual(pack["index"]["parsed"], 1)

    def test_malformed_cache_shapes_rebuild(self):
        self.demo()
        self.builder.refresh()
        path = self.root / ".qcb/index.json"
        for data in ([1], {"schema": 1, "root": str(self.root), "files": []},
                     {"schema": 1, "root": str(self.root), "files": {"maths.py": {"sha256": "x"}}}):
            path.write_text(json.dumps(data))
            self.assertEqual(self.builder.refresh()["parsed"], 4)

    def test_large_query_and_invalid_format(self):
        for kwargs in ({"query": ""}, {"query": "a" * 8001}, {"query": "a", "format": "xml"}, {"query": "a", "git_history": 501}):
            with self.assertRaises(ContextError):
                self.builder.build(**kwargs)


class UtilityTests(unittest.TestCase):
    def test_identifier_terms(self):
        found = terms("checkoutTotal round_amount")
        for term in ("checkout", "total", "round", "amount"):
            self.assertIn(term, found)

    def test_safe_paths(self):
        for path in ("../a.py", "/etc/passwords", "a/../../b", "a\\b", "a\n.py", ""):
            self.assertFalse(safe_relative(path))
        self.assertTrue(safe_relative("src/a.py"))

    def test_default_ignores(self):
        for path in (".env.example", "a/secrets.json", "a/credentials.py", ".aws/a.py", "node_modules/a.js", "a/key.pem"):
            self.assertFalse(allowed(path, []))

    def test_redaction_preserves_lines(self):
        raw = "first\npassword = 'fictional_password'\nlast\n"
        cleaned = redact(raw)
        self.assertEqual(len(raw.splitlines()), len(cleaned.splitlines()))
        self.assertNotIn("fictional_password", cleaned)

    def test_python_spans_do_not_overlap(self):
        text = "# header\nvalue = 1\n\n@decorator\ndef hello():\n    return value\n\n# footer\n"
        chunks = parse_file("a.py", text)["chunks"]
        seen = set()
        for chunk in chunks:
            lines = set(range(chunk["start"], chunk["end"] + 1))
            self.assertFalse(seen & lines)
            seen |= lines
        self.assertEqual(seen, set(range(1, 9)))


if __name__ == "__main__":
    unittest.main()
