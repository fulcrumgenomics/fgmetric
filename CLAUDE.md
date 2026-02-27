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

