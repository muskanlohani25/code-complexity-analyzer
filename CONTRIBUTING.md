# Contributing to Code Complexity Analyzer

First off, thank you for considering contributing to the Code Complexity Analyzer! It's people like you who make the open-source community such an amazing place to learn, inspire, and create.

## 🤝 How Can I Contribute?

### Reporting Bugs
If you find a bug, please create an issue containing:
- A clear description of the issue.
- The C++ source snippet that triggered the incorrect analysis.
- The expected vs. actual metrics (Time, Space, Cyclomatic Complexity, Smells).

### Submitting Pull Requests
1. Fork the repository and create your branch from `main`.
2. Install dependencies: `pip install -r requirements.txt`.
3. If you've added or modified parser code, write matching tests in `test_analyzer.py` or update `run_qa_audit.py`.
4. Ensure all unit and QA audit tests pass before submitting:
   ```bash
   python3 test_analyzer.py
   python3 run_qa_audit.py
   ```
5. Follow PEP 8 guidelines for Python and use consistent styles for HTML/CSS/JS.

## 📜 Style Guidelines

- **Python**: PEP 8 style, Google-style docstrings, type hints for all public functions.
- **JavaScript**: Modular, functional ES6 syntax. Avoid global variables.
- **CSS**: Curated custom properties (CSS variables) inside root, matching theme color maps.
