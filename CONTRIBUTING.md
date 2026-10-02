# Contributing

Use Python 3.10+ and the standard library for the core runtime. Keep external graph engines and model-specific tokenizers optional. Changes should add regression tests and preserve source provenance, truthful budget accounting and offline behavior.

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s examples/demo_repo -v
python examples/evaluate.py
python -m compileall -q quickcontext tests
```

For parser changes, test invalid syntax, aliases, imports, line ranges and misleading/dynamic calls. For retrieval changes, compare with `--no-graph` on a held-out query; do not leak an issue's answer patch into its historical hints. For budget changes, count the entire UTF-8 serialized output, not just source text. Tests must not require a network, paid API or user credentials.

Please include the command, expected result, actual result and a minimal public or synthetic reproduction when reporting a bug. Do not attach `.qcb` caches or private code. Contributions are under the project's MIT license; retain notices for any third-party code and verify license compatibility first.
