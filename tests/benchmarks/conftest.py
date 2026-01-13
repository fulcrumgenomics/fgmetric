from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def benchmark_data(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate benchmark data files and return the directory path."""
    data_dir = tmp_path_factory.mktemp("benchmark_data")

    header = "foo\tbar\tbaz\tabc\tghi\tjkl\n"
    row = f"1\thello\t1.2345\tworld\t\t{'A' * 500}\n"

    for num_rows, label in ((10_000, "1e4"), (100_000, "1e5")):
        tsv = data_dir / f"demo.{label}.tsv"
        with tsv.open("w") as f:
            f.write(header)
            for _ in range(num_rows):
                f.write(row)

    return data_dir
