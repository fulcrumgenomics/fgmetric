from abc import ABC
from csv import DictReader
from pathlib import Path
from typing import Any
from typing import Iterator
from typing import Type
from typing import TypeVar

from pydantic import BaseModel
from pydantic import model_validator

T = TypeVar("T", bound="Metric")


class Metric(BaseModel, ABC):
    """
    Abstract base class for defining structured metric data models.

    This class combines Pydantic's `BaseModel` with `ABC` to provide a foundation for creating
    type-safe metric classes that can be easily read from and written to delimited text files (e.g.,
    TSV, CSV). It leverages Pydantic's automatic validation and type conversion while providing
    convenient class methods for parsing metrics from files.

    Example:
        ```python
        class AlignmentMetric(Metric):
            read_name: str
            mapping_quality: int
            is_duplicate: bool = False

        # Read metrics from a TSV file
        for metric in AlignmentMetric.read(Path("metrics.txt")):
            print(metric.read_name, metric.mapping_quality)
        ```

    Note:
        Subclasses should define their fields using Pydantic field annotations.
        All field names in the input file should match the model field names or aliases.
        Empty fields are automatically converted to `None` during validation.
    """

    @classmethod
    def read(cls: Type[T], path: Path, delimiter: str = "\t") -> Iterator[T]:
        """Read Metric instances from file."""
        # NOTE: the utf-8-sig encoding is required to auto-remove BOM from input file headers
        with path.open(encoding="utf-8-sig") as fin:
            for record in DictReader(fin, delimiter=delimiter):
                yield cls.model_validate(record)

    @model_validator(mode="before")
    @classmethod
    def _empty_field_to_none(cls, data: Any) -> Any:
        """Treat any empty fields as None."""
        if isinstance(data, dict):
            for field, value in data.items():
                if value == "":
                    data[field] = None

        return data

    @classmethod
    def _header_fieldnames(cls, by_alias: bool = False) -> list[str]:
        """
        Return the fieldnames to use as a header row when writing metrics to a file.

        This method is used by `MetricWriter` to construct the underlying `csv.DictWriter`.
        It returns the fieldnames that will appear in serialized output, which may differ from
        the model's field names when aliases are used.

        Note:
            This method is deliberately not used during reading/validation. Note that the `read()`
            method omits the `fieldnames` parameter from `csv.DictReader` so that any missing or
            misspecified fields are handled by pydantic's model validation.

        Args:
            by_alias: If `True`, field aliases will be returned for fields that have them.

        Returns:
            The list of fieldnames to use as the header row.
        """
        # TODO: support returning the set of fields that would be constructed if the class has a
        # custom model serializer

        fieldnames: list[str]
        if by_alias:
            fieldnames = [
                field.alias if field.alias else fieldname
                for fieldname, field in cls.model_fields.items()
            ]
        else:
            fieldnames = list(cls.model_fields.keys())

        return fieldnames
