
from typing import Self
from pathlib import Path
from csv import DictWriter
from io import TextIOWrapper
from types import TracebackType
from collections.abc import Iterable
from contextlib import AbstractContextManager

from fgmetric.metric import Metric


class MetricWriter[T: Metric](AbstractContextManager):
    """
    Context manager for writing :class:`Metric` instances to delimited text files.

    ``MetricWriter`` serializes ``Metric`` objects to TSV, CSV, or any other single-character
    delimited format. The header row is written automatically on construction using
    :meth:`Metric._header_fieldnames`, which correctly expands ``Counter[StrEnum]`` fields into
    one column per enum member.

    All pydantic serializers registered on the ``Metric`` subclass (list joining,
    counter pivoting, etc.) are applied automatically via :meth:`pydantic.BaseModel.model_dump`.

    Use as a context manager to guarantee the underlying file is closed even if an exception
    occurs during writing:

    Example:
        ```python
        class AlignmentMetric(Metric):
            read_name: str
            mapping_quality: int
            is_duplicate: bool = False

        metrics = [
            AlignmentMetric(read_name="read1", mapping_quality=60, is_duplicate=False),
            AlignmentMetric(read_name="read2", mapping_quality=30, is_duplicate=True),
        ]

        with MetricWriter(AlignmentMetric, Path("output.tsv")) as writer:
            writer.writeall(metrics)
        ```

    Note:
        The output file is opened with ``encoding="utf-8"`` to match the ``utf-8-sig``
        encoding used by :meth:`Metric.read` (the BOM is stripped on reading, not written).

    Note:
        The file is opened and the header is written immediately in ``__init__``, before
        ``__enter__`` is called. Always use the context manager form (``with`` statement)
        to ensure the file is properly closed.
    """

    _metric_class: type[T]
    _fout: TextIOWrapper
    _writer: DictWriter[str]

    def __init__(
        self,
        metric_class: type[T],
        filename: Path | str,
        delimiter: str = "\t",
        lineterminator: str = "\n",
    ) -> None:
        """
        Open *filename* for writing and write the header row immediately.

        Args:
            metric_class: The :class:`Metric` subclass whose instances will be written.
                Determines the header columns via :meth:`Metric._header_fieldnames`.
            filename: Path to the output file. Created if it does not exist; truncated
                if it does.
            delimiter: Single-character field separator. Defaults to ``"\\t"`` (TSV).
            lineterminator: String used to terminate each written row. Defaults to ``"\\n"``.
        """
        self._metric_class = metric_class
        # Explicit UTF-8 encoding ensures consistent output across platforms (avoids the
        # system-default encoding on Windows, e.g. cp1252).
        self._fout = Path(filename).open("w", encoding="utf-8")
        self._writer = DictWriter(
            f=self._fout,
            fieldnames=self._metric_class._header_fieldnames(),
            delimiter=delimiter,
            lineterminator=lineterminator,
        )
        self._writer.writeheader()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
        super().__exit__(exc_type, exc_value, traceback)

    def close(self) -> None:
        """Flush and close the underlying file handle."""
        self._fout.close()

    def write(self, metric: T) -> None:
        """
        Serialize *metric* and write it as a single row.

        The metric is serialized to a JSON-compatible dict via
        ``metric.model_dump(mode="json")``, which ensures all pydantic serializers run
        (list joining, counter pivoting, enum coercion, etc.) and that all values are
        JSON-primitive types (``str``, ``int``, ``float``, ``bool``, ``None``) rather than
        raw Python objects. ``DictWriter`` then writes the dict as a delimited row.

        Args:
            metric: A validated instance of the ``Metric`` subclass this writer was
                constructed with.
        """
        self._writer.writerow(metric.model_dump(mode="json"))

    def writeall(self, metrics: Iterable[T]) -> None:
        """
        Serialize and write each metric in *metrics* as a row.

        Equivalent to calling :meth:`write` for each element. The iterable is consumed
        lazily, so generators and other single-pass iterables are fully supported.

        Args:
            metrics: Any iterable of validated ``Metric`` instances.
        """
        for metric in metrics:
            self.write(metric)
