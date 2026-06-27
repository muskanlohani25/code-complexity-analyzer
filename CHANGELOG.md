# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-06-28
### Added
- Added PEP 8 type hints and annotations to the entire Python codebase (`analyzer.py`, `helpers.py`, `routes.py`, `app.py`).
- Integrated automated QA verification suite `run_qa_audit.py` with 50 distinct C++ test cases.
- Generated open-source community guidelines (`LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `requirements.txt`, `.gitignore`).

### Fixed
- Fixed a preprocessor macro collision where `#define` values were incorrectly treated as part of subsequent function declarations.
- Fixed `do-while` loop double counting in Cyclomatic Complexity.
- Fixed a BFS/DFS loop multiplication bug where nested graph queue iterations were incorrectly evaluated as $O(n^2)$ instead of linear $O(n)$.
- Fixed false-positive infinite loops checking inside standard block comments.
- Fixed low constant bounds checking in count-down loops (e.g. `j >= 0` evaluated to linear rather than constant).
- Fixed mutual recursion analysis where cyclical calls (A -> B -> A) were missed.
- Fixed duplicate map suggestions being appended twice in `analyzer.py`.

---

## [1.1.0] - 2026-06-27
### Added
- Added circular Code Quality overall scores and category breakdowns.
- Added Cyclomatic Complexity counting (overall value, risk tags, and branch logs).
- Added Code Smell detection (magic numbers, deep nesting, long functions, large parameter lists, mutable globals, duplicate loops).
- Added export capabilities for JSON metrics and print-friendly PDF generation via `html2pdf.js`.
- Added copy-to-clipboard summary formatter.

---

## [1.0.0] - 2026-06-25
### Added
- Initial release of the Code Complexity Analyzer.
- Standard loops complexity estimation (time and auxiliary space metrics).
- C++ brace matching preprocessor.
- IDE-style UI with line numbers synchronization.
