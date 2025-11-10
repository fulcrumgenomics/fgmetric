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

-------------------------------------------------------------------------- benchmark 'num_rows=1e4': 2 tests --------------------------------------------------------------------------
Name (time in ms)          Min                Max               Mean            StdDev             Median               IQR            Outliers       OPS            Rounds  Iterations
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_fgmetric[1e4]      4.1870 (1.0)      10.4346 (1.0)       4.3487 (1.0)      0.6808 (1.0)       4.2255 (1.0)      0.0569 (1.0)          5;16  229.9554 (1.0)         210           1
test_fgpyo[1e4]        24.6707 (5.89)     28.2135 (2.70)     25.9577 (5.97)     1.2724 (1.87)     25.4868 (6.03)     2.5392 (44.61)        12;0   38.5243 (0.17)         36           1
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

-------------------------------------------------------------------------------- benchmark 'num_rows=1e5': 2 tests --------------------------------------------------------------------------------
Name (time in ms)             Min                   Max                  Mean             StdDev                Median                IQR            Outliers     OPS            Rounds  Iterations
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_fgmetric[1e5]       511.5684 (1.0)        544.4664 (1.0)        525.3263 (1.0)      13.7011 (1.33)       520.4601 (1.0)      22.1126 (1.53)          2;0  1.9036 (1.0)           5           1
test_fgpyo[1e5]        2,534.3935 (4.95)     2,559.5660 (4.70)     2,543.6455 (4.84)     10.3042 (1.0)      2,538.5802 (4.88)     14.4195 (1.0)           1;0  0.3931 (0.21)          5           1
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```
