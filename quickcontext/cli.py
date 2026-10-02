"""Command-line interface; all analysis stays on the local machine."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .core import Builder, ContextError


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qcb", description="Build offline, size-bounded code context for a question")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    index = sub.add_parser("index", help="Create/refresh a local incremental index")
    index.add_argument("repo", nargs="?", default=".")
    cases = sub.add_parser("import-cases", help="Replace local resolved-case hints from a JSON array")
    cases.add_argument("repo")
    cases.add_argument("file", type=Path)
    build = sub.add_parser("build", help="Refresh and select current source for a question")
    build.add_argument("repo", nargs="?", default=".")
    query = build.add_mutually_exclusive_group(required=True)
    query.add_argument("--query", "-q")
    query.add_argument("--query-file", type=Path, help="UTF-8 issue/question file; no remote fetching")
    build.add_argument("--token-budget", type=int, default=3000,
                       help="Cap estimated tokens: ceil(UTF-8 output bytes / 2), NOT model tokens (default: 3000)")
    build.add_argument("--max-bytes", type=int, help="Additional hard cap on the complete UTF-8 output")
    build.add_argument("--format", choices=("markdown", "json"), default="markdown")
    build.add_argument("--git-history", type=int, default=0, metavar="N",
                       help="Opt in to the latest N commit subjects and changed-path hints (max 500)")
    build.add_argument("--no-graph", action="store_true", help="Disable relationship expansion for comparison")
    build.add_argument("--output", "-o", type=Path, help="Write the complete pack to this file instead of stdout")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        builder = Builder(args.repo)
        if args.command == "index":
            print(json.dumps(builder.refresh(), sort_keys=True))
        elif args.command == "import-cases":
            print(json.dumps({"imported": builder.import_cases(args.file)}))
        else:
            if args.query_file:
                if args.query_file.stat().st_size > 32_000:
                    raise ContextError("Query file exceeds 32 KB")
                query = args.query_file.read_text(encoding="utf-8")
            else:
                query = args.query
            _, output = builder.build(query, token_budget=args.token_budget, max_bytes=args.max_bytes,
                                      format=args.format, git_history=args.git_history, graph=not args.no_graph)
            if args.output:
                args.output.write_text(output, encoding="utf-8")
            else:
                sys.stdout.write(output)
        return 0
    except (ContextError, OSError, UnicodeError) as exc:
        print(f"qcb: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
