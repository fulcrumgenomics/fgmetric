# fgmetric: Pydantic-backed Metrics


[![CI](https://github.com/fulcrumgenomics/fgmetric/actions/workflows/python_package.yml/badge.svg?branch=main)](https://github.com/fulcrumgenomics/fgmetric/actions/workflows/python_package.yml?query=branch%3Amain)
[![Python Versions](https://img.shields.io/badge/python-3.12_|_3.13-blue)](https://github.com/fulcrumgenomics/fgmetric)
[![MyPy Checked](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)

This package provides a proof-of-concept alternative implementation of `fgpyo.util.metric.Metric`, using `pydantic` for runtime type validation and coercion.

### Key features:

- **Speed**.
  By using `pydantic` for type coercion, this implementation can yield a ~5-6x speedup in some workflows compared to pure Python reflection.
  ([See benchmarks below.](#Benchmarks-vs-fgpyo))
- **Support for comma-delimited files.**
  This provides additional flexibility when working with user-provided delimited data files.
- **Lightweight dependencies.**
  Requires only `pydantic`, with no need for `attrs` or `pysam`.

### Other notable differences:

- Simplified usage: No need to decorate with `@dataclass` or `@attr.s`, just subclass `Metric`.
- Cleaner type signatures: `Metric.read()` returns a properly typed iterable, rather than `Iterator[Any]`.
- Reduced boilerplate: `Metric` is no longer a self-referential generic, so no recursive type annotation.

### Example:

```py
from fgmetric import Metric


class DemoMetric(Metric):
    foo: str
    bar: int


# type hint optional: `mypy` will infer metrics to be `Iterator[DemoMetric]`
metrics =  DemoMetric.read("path/to/demo.tsv")
```

## Recommended Installation

Install the Python package and dependency management tool [`uv`](https://docs.astral.sh/uv/getting-started/installation/) using official documentation.

Install the project and its dependencies with:

```console
uv sync --locked
```

## Development and Testing

See the [contributing guide](./CONTRIBUTING.md) for more information.

## Benchmarks vs `fgpyo`

On example files with 10,000 and 100,000 rows, using `pydantic` speeds up `Metric` parsing by 5-6 fold.

```console
$ uv run --extra benchmark poe benchmark

========================================================================================================================== tests coverage ==========================================================================================================================

-------------------------------------------------------------------------- benchmark 'num_rows=1e4': 2 tests --------------------------------------------------------------------------
Name (time in ms)          Min                Max               Mean            StdDev             Median               IQR            Outliers       OPS            Rounds  Iterations
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_fgmetric[1e4]      4.4234 (1.0)      10.2758 (1.0)       4.7227 (1.0)      0.7380 (1.0)       4.5997 (1.0)      0.1114 (1.0)          4;10  211.7432 (1.0)         178           1
test_fgpyo[1e4]        28.0971 (6.35)     35.8240 (3.49)     28.9853 (6.14)     1.4279 (1.93)     28.8047 (6.26)     0.5033 (4.52)          2;3   34.5003 (0.16)         36           1
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

-------------------------------------------------------------------------------- benchmark 'num_rows=1e5': 2 tests --------------------------------------------------------------------------------
Name (time in ms)             Min                   Max                  Mean             StdDev                Median                IQR            Outliers     OPS            Rounds  Iterations
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_fgmetric[1e5]       542.4160 (1.0)        575.0789 (1.0)        554.7240 (1.0)      14.3811 (1.14)       547.1858 (1.0)      23.3336 (1.0)           1;0  1.8027 (1.0)           5           1
test_fgpyo[1e5]        2,925.8016 (5.39)     2,951.7295 (5.13)     2,939.9166 (5.30)     12.6617 (1.0)      2,943.4470 (5.38)     24.5220 (1.05)          1;0  0.3401 (0.19)          5           1
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```
