# fgmetric


[![CI](https://github.com/fulcrumgenomics/fgmetric/actions/workflows/python_package.yml/badge.svg?branch=main)](https://github.com/fulcrumgenomics/fgmetric/actions/workflows/python_package.yml?query=branch%3Amain)
[![Python Versions](https://img.shields.io/badge/python-3.11_|_3.12_|_3.13-blue)](https://github.com/fulcrumgenomics/fgmetric)
[![MyPy Checked](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)

Pydantic-backed Metric.

## Recommended Installation

Install the Python package and dependency management tool [`uv`](https://docs.astral.sh/uv/getting-started/installation/) using official documentation.
You must have Python 3.11 or greater available on your system path, which could be managed by [`mamba`](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html), [`pyenv`](https://github.com/pyenv/pyenv), or another package manager. 
Finally, install the dependencies of the project with:

```console
uv sync --locked --extra=dev
```

To check successful installation, run:

```console
uv run fgmetric hello --name Fulcrum
```

## Development and Testing

See the [contributing guide](./CONTRIBUTING.md) for more information.
