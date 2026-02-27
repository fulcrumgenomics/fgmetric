from pathlib import Path
from typing import assert_type
from unittest import mock

import pytest

from fgmetric import Metric
from fgmetric import MetricWriter


class FakeMetric(Metric):
    """A fake Metric to use in tests."""

    foo: str
    bar: int


def test_writer(tmp_path: Path) -> None:
    """Test we can write a Metric to file."""
    fpath = tmp_path / "test.txt"

    writer: MetricWriter[FakeMetric]
    with MetricWriter(FakeMetric, fpath) as writer:
        assert_type(writer, MetricWriter[FakeMetric])
        writer.write(FakeMetric(foo="abc", bar=1))
        writer.write(FakeMetric(foo="def", bar=2))

    with fpath.open("r") as f:
        assert next(f) == "foo\tbar\n"
        assert next(f) == "abc\t1\n"
        assert next(f) == "def\t2\n"
        with pytest.raises(StopIteration):
            next(f)


def test_init_closes_file_on_failure(tmp_path: Path) -> None:
    """Test that the file handle is closed if __init__ raises after opening."""
    fpath = tmp_path / "test.txt"
    fpath.touch()
    real_fout = fpath.open("w")

    with (
        mock.patch("fgmetric.metric_writer.Path.open", return_value=real_fout),
        mock.patch.object(FakeMetric, "_header_fieldnames", side_effect=ValueError("boom")),
        pytest.raises(ValueError, match="boom"),
    ):
        MetricWriter(FakeMetric, fpath)

    assert real_fout.closed
