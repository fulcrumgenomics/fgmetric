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
    """Abstract base class for pydantic-based Metrics."""

    @classmethod
    def read(cls: Type[T], path: Path, delimiter: str = "\t") -> Iterator[T]:
        """Read Metric instances from file."""
        # NOTE: the utf-8-sig encoding is required to auto-remove BOM from input file headers
        with path.open(encoding="utf-8-sig") as fin:
            for record in DictReader(fin, delimiter=delimiter):
                yield cls.model_validate(record)

    @model_validator(mode="before")
    @classmethod
    def empty_field_to_none(cls, data: Any) -> Any:
        """Treat any empty fields as None."""
        if isinstance(data, dict):
            for field, value in data.items():
                if value == "":
                    data[field] = None

        return data

    @classmethod
    def fieldnames(cls, by_alias: bool = False) -> list[str]:
        """
        Get the metric's fieldnames.

        Args:
            by_alias: If `True`, field aliases will be returned for fields that have them.
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
