# Repository Guidelines

## Project Structure & Module Organization
- `gateway/` holds the CLI entry point (`gateway/imessage_client.py`) and command wiring.
- `src/` contains core logic (contacts, message interface, scheduling) plus RAG modules in `src/rag/`.
- `tests/` contains pytest suites named `test_*.py`.
- `scripts/` contains maintenance utilities like contact sync.
- `config/` holds templates and local config (personal data stays out of git).
- `benchmarks/` and `mcp_server_archive/` are auxiliary, not required for core runtime.

## Build, Test, and Development Commands
- `pip install -r requirements.txt`: install Python dependencies.
- `python3 gateway/imessage_client.py --help`: verify CLI wiring and available commands.
- `python3 scripts/sync_contacts.py`: sync contacts from macOS Contacts.
- `pytest tests/ -v`: run the full test suite.
- `pytest tests/test_contacts_sync.py -v`: run a targeted test file.
- `python3 -m Texting.benchmarks.run_benchmarks`: run performance benchmarks.

## Coding Style & Naming Conventions
- Python 3.9+, 4-space indentation, module-level docstrings are common.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- Use `pathlib.Path` and resolve paths from the repository root instead of assuming CWD.

## Testing Guidelines
- Use `pytest`; keep new tests in `tests/` with `test_*.py` naming.
- Prefer deterministic unit tests; isolate macOS-specific behavior behind small interfaces.
- Add coverage-oriented tests when touching parsing or search logic.

## Commit & Pull Request Guidelines
- Commit messages follow Conventional Commits, e.g., `feat(gateway): add CLI command` or `fix(rag): handle empty index`.
- Keep subjects short and imperative; include a scope when it clarifies the area.
- PRs should include: a concise summary, testing notes, and any macOS permission requirements.
- Do not commit personal data. Files like `config/contacts.json`, `data/`, and `logs/` are gitignored for a reason.

## Security & Configuration Tips
- The app reads from `~/Library/Messages/chat.db`; Full Disk Access is required on macOS.
- Start from `config/contacts.example.json` when creating local config.
