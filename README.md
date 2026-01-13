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

On example files with 10,000 and 100,000 rows, using `pydantic` speeds up `Metric` parsing by ~5 fold.

```console
$ uv run --extra benchmark poe benchmark

--------------------------------------------------------------------------- benchmark 'num_rows=1e4': 2 tests ----------------------------------------------------------------------------
Name (time in ms)           Min                 Max                Mean            StdDev              Median               IQR            Outliers      OPS            Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_fgmetric[1e4]      46.9850 (1.0)       56.2292 (1.0)       50.3851 (1.0)      3.3265 (1.0)       49.1207 (1.0)      6.4517 (1.02)          6;0  19.8471 (1.0)          18           1
test_fgpyo[1e4]        270.8720 (5.77)     282.5591 (5.03)     275.4368 (5.47)     4.5861 (1.38)     274.8490 (5.60)     6.3225 (1.0)           1;0   3.6306 (0.18)          5           1
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

-------------------------------------------------------------------------------- benchmark 'num_rows=1e5': 2 tests --------------------------------------------------------------------------------
Name (time in ms)             Min                   Max                  Mean             StdDev                Median                IQR            Outliers     OPS            Rounds  Iterations
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_fgmetric[1e5]       548.3379 (1.0)        579.5940 (1.0)        563.7652 (1.0)      12.6133 (1.21)       564.8853 (1.0)      20.6046 (1.27)          2;0  1.7738 (1.0)           5           1
test_fgpyo[1e5]        2,764.4992 (5.04)     2,790.0149 (4.81)     2,775.1369 (4.92)     10.4317 (1.0)      2,776.1375 (4.91)     16.2167 (1.0)           2;0  0.3603 (0.20)          5           1
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```
