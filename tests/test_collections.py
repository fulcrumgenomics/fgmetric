from pathlib import Path

import pytest

from fgmetric import Metric
from fgmetric import MetricWriter
from fgmetric.collections import CommaDelimitedList


def test_comma_delimited_list_of_int(tmp_path: Path) -> None:
    """Test that we can read and write comma-delimited lists."""

    class FakeMetric(Metric):
        name: str
        values: CommaDelimitedList[int]

    # Test reading
    fpath_to_read = tmp_path / "test.txt"
    with fpath_to_read.open("w") as fout:
        fout.write("name\tvalues\n")
        fout.write("Nils\t1,2,3\n")

    metrics = list(FakeMetric.read(fpath_to_read))

    assert len(metrics) == 1
    assert metrics[0].name == "Nils"
    assert metrics[0].values == [1, 2, 3]

    # Test writing
    fpath_to_write = tmp_path / "written.txt"
    writer: MetricWriter[FakeMetric]
    with MetricWriter(FakeMetric, fpath_to_write) as writer:
        writer.write(FakeMetric(name="Tim", values=[4, 5, 6]))

    with fpath_to_write.open("r") as f:
        assert next(f) == "name\tvalues\n"
        assert next(f) == "Tim\t4,5,6\n"
        with pytest.raises(StopIteration):
            next(f)


def test_comma_delimited_list_of_float(tmp_path: Path) -> None:
    """Test that we can read and write comma-delimited lists."""

    class FakeMetric(Metric):
        name: str
        values: CommaDelimitedList[float]

    ################################################################################################
    # Test reading
    ################################################################################################
    fpath_to_read = tmp_path / "test.txt"
    with fpath_to_read.open("w") as fout:
        fout.write("name\tvalues\n")
        fout.write("Nils\t1.0,2.5,3.14159\n")

    metrics = list(FakeMetric.read(fpath_to_read))

    assert len(metrics) == 1
    assert metrics[0].name == "Nils"
    assert metrics[0].values == pytest.approx([1.0, 2.5, 3.14159])

    ################################################################################################
    # Test writing
    ################################################################################################
    fpath_to_write = tmp_path / "written.txt"

    writer: MetricWriter[FakeMetric]
    with MetricWriter(FakeMetric, fpath_to_write) as writer:
        writer.write(FakeMetric(name="Tim", values=[3.0, 4.5, 2.718]))

    with fpath_to_write.open("r") as f:
        assert next(f) == "name\tvalues\n"
        assert next(f) == "Tim\t3.0,4.5,2.718\n"
        with pytest.raises(StopIteration):
            next(f)


def test_comma_delimited_list_of_str(tmp_path: Path) -> None:
    """Test that we can read and write comma-delimited lists."""

    class FakeMetric(Metric):
        name: str
        values: CommaDelimitedList[str]

    ################################################################################################
    # Test reading
    ################################################################################################
    fpath_to_read = tmp_path / "test.txt"
    with fpath_to_read.open("w") as fout:
        fout.write("name\tvalues\n")
        fout.write("Nils\ta,2,3.14,foo\n")

    metrics = list(FakeMetric.read(fpath_to_read))

    assert len(metrics) == 1
    assert metrics[0].name == "Nils"
    assert metrics[0].values == ["a", "2", "3.14", "foo"]

    ################################################################################################
    # Test writing
    ################################################################################################
    fpath_to_write = tmp_path / "written.txt"

    writer: MetricWriter[FakeMetric]
    with MetricWriter(FakeMetric, fpath_to_write) as writer:
        writer.write(FakeMetric(name="Tim", values=["b", "3", "2.718", "bar"]))

    with fpath_to_write.open("r") as f:
        assert next(f) == "name\tvalues\n"
        assert next(f) == "Tim\tb,3,2.718,bar\n"
        with pytest.raises(StopIteration):
            next(f)
