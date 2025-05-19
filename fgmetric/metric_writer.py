from contextlib import AbstractContextManager
from csv import DictWriter
from io import TextIOWrapper
from pathlib import Path
from types import TracebackType
from typing import Iterable
from typing import Type

from fgmetric.metric import Metric


class MetricWriter[T: Metric](AbstractContextManager):
    """Write Metric instances to file."""

    _metric_class: type[T]
    _fout: TextIOWrapper
    _writer: DictWriter

    def __init__(
        self,
        metric_class: type[T],
        filename: Path | str,
        delimiter: str = "\t",
        lineterminator: str = "\n",
    ) -> None:
        """
        Initialize a new `MetricWriter`.

        Args:
            filename: Path to the file to write.
            metric_class: Metric class.
            delimiter: The output file delimiter.
            lineterminator: The string used to terminate lines produced by the MetricWriter.

        Raises:
            TypeError: If the provided metric class is not a subclass of `Metric`.
        """
        self._metric_class = metric_class
        self._fout = Path(filename).open("w")

        self._writer = DictWriter(
            f=self._fout,
            fieldnames=self._metric_class.fieldnames(),
            delimiter=delimiter,
            lineterminator=lineterminator,
        )

        self._writer.writeheader()

    def __enter__(self) -> "MetricWriter":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        self.close()
        super().__exit__(exc_type, exc_value, traceback)

    def close(self) -> None:
        """Close the underlying file handle."""
        self._fout.close()

    def write(self, metric: T) -> None:
        """
        Write a single Metric instance to file.

        The Metric is converted to a dictionary and then written using the underlying `DictWriter`.

        Args:
            metric: An instance of the specified Metric.

        Raises:
            TypeError: If the provided `metric` is not an instance of the Metric class used to
                parametrize the writer.
        """
        self._writer.writerow(metric.model_dump())

    def writeall(self, metrics: Iterable[T]) -> None:
        """
        Write multiple Metric instances to file.

        Each Metric is converted to a dictionary and then written using the underlying `DictWriter`.

        Args:
            metrics: A sequence of instances of the specified Metric.
        """
        for metric in metrics:
            self.write(metric)
