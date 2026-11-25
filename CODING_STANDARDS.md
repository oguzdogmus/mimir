# Coding standards

Judgement rules for `scripts/` and `tests/`. Mechanical rules (text encoding, private imports) are checked by ruff (`ruff.toml`) and the tests; they are not repeated here.

- **Safety checkers fail closed.** A checker that guards what reaches the student (the page and SVG allowlists, input fields, labels) refuses anything it does not consume or does not know. It never drops, skips or passes through an unknown element, attribute or field. Example: `workspace.check_keys` refuses any unknown input field.
- **One owner per default value.** A default (a path, a limit, a token, a label) is defined once, in the module that owns it, and other modules read it from there. Do not repeat the literal.
- **Find places through the helpers.** The learning root, the profile and course folders come from the `workspace` and `ingest` helpers (`workspace.resolve_root`, `workspace.course_folder`), never from path arithmetic such as `Path.home() / "learning"`. The helpers carry the pointer rule and the symlink and name checks.
- **Renames remove every old identifier.** When a name changes, change every use, docstring and doc in the same change. No alias that keeps the old name alive.
- **Scripts keep the JSON contract.** One JSON object in on stdin, one JSON object out on stdout with a ready-to-print `line`. Bad input exits 2 with one stderr line that names the field (`unknown field 'x'`, `exam_date must be a date`); anything else exits 1 as an internal error, never a traceback. Files are written atomically: a temp file in the same folder, then `os.replace`.
- **Tests drive scripts from outside.** A test feeds JSON in through the CLI (a subprocess, `main()` or a `cmd_*` handler) and checks the JSON and the files that come out. Reach for an internal helper only for what the CLI cannot reach, such as an OS opener or a platform probe.
