# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**fgmetric** is a Python 3.12+ library for reading and writing delimited metric files (TSV/CSV) using Pydantic v2 models. It serves as a faster alternative to `fgpyo.util.metric.Metric` (5-6x speedup via Pydantic v2 type coercion).

## Commands

```bash
# Setup
uv sync --locked
uv run pre-commit install --hook-type pre-push

# Fix formatting and linting, then check types and tests (pre-push hook runs this)
uv run poe fix-and-check-all

# Individual checks
uv run poe check-format       # ruff format --check --diff
uv run poe check-lint         # ruff check
uv run poe check-typing       # mypy
uv run poe check-tests        # pytest (excludes benchmarks)
uv run poe check-all          # all checks

# Individual fixes
uv run poe fix-format         # ruff format
uv run poe fix-lint           # ruff check --fix

# Run a single test
uv run pytest tests/test_metric.py::TestClassName::test_name

# Benchmarks (requires optional dependency)
uv run --extra benchmark poe benchmark
```

## Architecture

The public API is two classes: `Metric` (read) and `MetricWriter` (write), exported from `fgmetric/__init__.py`.

**`Metric`** (`fgmetric/metric.py`) — Abstract base class for defining metric types. Inherits from Pydantic `BaseModel` plus two mixins. Users subclass it and call `MyMetric.read(path)` to parse delimited files. A `_empty_field_to_none` model validator (mode="before") converts empty strings to `None` for optional fields.

**`MetricWriter`** (`fgmetric/metric_writer.py`) — Generic context manager (`MetricWriter[T: Metric]`) wrapping `csv.DictWriter`. Writes header on init, serializes metrics via `model_dump()`.

**Mixins** (in `fgmetric/collections/`):
- **`DelimitedList`** (`_delimited_list.py`) — Transparently converts `list[T]` fields to/from comma-delimited strings. Configurable via `collection_delimiter` ClassVar. Uses field validator (split) and field serializer (join).
- **`CounterPivotTable`** (`_counter_pivot_table.py`) — Pivots a `Counter[StrEnum]` field into one column per enum member. At most one Counter field per Metric; must be non-optional StrEnum. Uses model validator (collect) and model serializer (pivot).

**`_typing_extensions.py`** — Internal helpers for type annotation introspection (`is_optional`, `unpack_optional`, `is_list`, `is_counter`, `has_origin`).

**Mixin MRO**: `Metric(DelimitedList, CounterPivotTable, BaseModel, ABC)`. Both mixins use `__pydantic_init_subclass__()` to cache field metadata at class definition time.

## Conventions

- **Type hints**: Strict mypy (all strict flags enabled). Use modern syntax: `T | None`, `list[T]`, `type[T]`.
- **Docstrings**: Google-style, enforced by ruff. Summary on second line after opening quotes (D213 selected, D212 ignored).
- **Line length**: 100 characters.
- **Imports**: Force single-line (`isort.force-single-line = true`).
- **Linting**: Ruff with preview mode. B rules are unfixable (manual fix required). Test files exempt from D103 (missing docstring).
- **Testing**: pytest with `--import-mode=importlib`. Use `tmp_path` fixture for file I/O. Parametrize tests for multiple scenarios.
- **Git discipline**: Explicit `git add {filepath}` (never `git add .`). Commits scoped to <400 lines of diff.

## Core Principles

**Priority order:** Correctness → Readability → Simplicity → Performance

1. **Correctness:** Structure code to be testable; isolate complex logic for unit testing.
2. **Readability:** If you'd change it on a rewrite, refactor now.
3. **Simplicity:** Prefer recognizable patterns. Don't introduce new patterns without discussion.
4. **Performance:** Correct implementation first. Ask and profile before optimizing.

## Git Workflow

### Commit Granularity

Commit after completing one of:
- A single function/method implementation
- One refactoring step (rename, extract, move)
- A bug fix with its regression test
- A documentation update

**Size guidelines:**
- Per commit: 100–300 lines preferred, 400 max
- Per PR: No hard limit, but consider splitting if >800 lines or >5 unrelated files

**Good commit scope examples:**
- `Add FastaIndex.validate() method`
- `Rename species_map → species_to_ref_fasta_map`
- `Fix off-by-one in BED coordinate parsing`

### Commit Messages

```
Concise title in imperative mood (<72 chars)

Detailed body explaining:
- What changed
- Why (link issues with "Closes #123" or "Related to #456")
- Any non-obvious implementation choices
```

### Commit Rules
- Run `uv run poe fix-and-check-all` before each commit; all checks must pass
- No merge commits
- Do not rebase without explicit user approval
- Use `git mv` for file moves; if moving *and* editing, make two commits (move first, then edits)
- **Never mix formatting and functional changes.** If unavoidable, isolate formatting into separate commits at start or end of branch.

### Pull Requests
- Title: Imperative mood, <72 chars (e.g., "Add FASTA index validation")
- Body: What changed, why, testing done, migration notes if applicable
- Link issues: "Closes #123" or "Related to #456"

### Branch Hygiene
- Use `.gitignore` liberally
- Never commit: IDE files, personal test files, local debug data, commented-out code

## Code Style

### Organization
- Extract logic into small–medium functions with clear inputs/outputs
- Scope variables tightly; limit visibility to where needed
- Use block comments for visual separation when function extraction isn't practical

### Naming
- Meaningful names, even if long: `species_to_ref_fasta_map` not `species_map`
- Short names only for tight scope (loop indices, single-line lambdas)
- Signal behavior in function names: `to_y()`, `is_valid()` → returns value; `update_x()` → side effect

### Documentation

**Doc comments (required on all public functions/classes):**
- What it does
- Parameters and return value
- Constraints, exceptions raised, side effects

**Code comments:**
- Explain non-obvious choices and complex logic
- Never comment self-evident code

### Type Signatures
- **Parameters:** Accept the most general type practical (e.g., `Iterable` over `List`)
- **Returns:** Return the most specific type without exposing implementation details

### Functions
- Functions should have **either** returns **or** side effects, not both
- Exceptions: logging, caching (where side effect is performance-only)

### Pragmatism
- Balance functional, OOP, and imperative—use what's clearest
- When in doubt, prefer pure functions and immutable data
- Know your utility libraries; contribute upstream rather than writing one-offs

## Error Handling

- Fail fast with informative messages at I/O boundaries
- Never silently swallow exceptions; log or re-raise with context
- When a loop may generate multiple errors, collect them and raise once at the end
- Error messages should include: what failed, why, and how to fix (if known)

## Testing

### Principles
- Generate test data programmatically; avoid committing test data files
- Test behavior, not implementation—tests should survive refactoring
- Cover: expected behavior, error conditions, boundary cases
- Scale rigor to code longevity: thorough for shared code, lighter for one-off scripts

### Coverage Expectations
- New public functions: at least one happy-path test + one error case
- Bug fixes: add a regression test that would have caught the bug
- Performance-critical code: include benchmark or explain in PR why not needed

## Documentation Maintenance

When modifying code, update as needed:
- [ ] Docstrings (if signature or behavior changed)
- [ ] CHANGELOG.md (if user-facing)
- [ ] README.md (if usage patterns changed)
- [ ] Migration notes (if breaking change)

Reference issue/PR numbers in CHANGELOG entries.

## Python-Specific

### Style
- Heavier use of classes and type annotations than typical Python
- Prefer `@dataclass(frozen=True)` and Pydantic models with `frozen=True`
- Isolate I/O at module boundaries; keep core logic as pure functions

### Typing
- **Required:** Type annotations on all function parameters and returns
- Annotate locals when: they become return values, or called function lacks hints
- Use type aliases or `NewType` for complex structures
- Avoid `Any`—prefer type alias or `TypeVar`

