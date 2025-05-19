from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def benchmark_data() -> Path:
    """Path to the benchmark data directory."""
    return Path(__file__).parent / "data"
