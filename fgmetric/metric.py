from abc import ABC
from collections.abc import Iterator
from csv import DictReader
from pathlib import Path
from typing import Any
from typing import Self

from pydantic import model_validator

from fgmetric._typing_extensions import is_optional
from fgmetric.collections import CounterPivotTable
from fgmetric.collections import DelimitedList


class Metric(
    DelimitedList,
    CounterPivotTable,
    ABC,
):
    """
    Abstract base class for structured metric data models backed by delimited text files.

    Subclasses define their columns as pydantic-annotated fields; ``Metric`` handles all
    serialization and deserialization to and from delimited files (TSV, CSV, etc.).

    **MRO and mixin order**

    The parent-class order is significant. Python's MRO ensures that ``DelimitedList`` and
    ``CounterPivotTable`` validators and serializers run before ``BaseModel``'s defaults.
    ``BaseModel`` is inherited transitively through the mixins and must not be listed
    explicitly (doing so is redundant and can mislead readers about the true MRO)::

        Metric → DelimitedList → CounterPivotTable → BaseModel → ABC

    Do **not** reorder ``DelimitedList`` and ``CounterPivotTable`` — validators may
    silently stop firing.

    **Built-in deserialization behaviours**

    1. **Empty string → ``None``.**  Any empty string (``""``) in an input row is converted to
       ``None`` before field validation, provided the field is annotated as optional
       (``T | None``).  This happens before all other validators so that downstream logic
       never needs to handle bare empty strings.

    2. **Delimited lists.**  Fields annotated as ``list[T]`` are split from a delimited string
       on validation and joined back on serialization. The delimiter is controlled by the
       ``collection_delimiter`` class variable (default ``","``).

    3. **Counter pivot tables.**  Fields annotated as ``Counter[StrEnum]`` are deserialized by
       folding wide-format enum-valued columns into a single ``Counter``, and serialized by
       pivoting them back out.  See :class:`CounterPivotTable` for details.

    Class Variables:
        collection_delimiter: Single-character delimiter for ``list[T]`` fields (inherited
            from :class:`DelimitedList`, default ``","``).

    Example:
        Define a metric:

        ```python
        class AlignmentMetric(Metric):
            read_name: str
            mapping_quality: int
            is_duplicate: bool = False
        ```

        Read from a TSV file (one ``AlignmentMetric`` instance per row):

        ```python
        for metric in AlignmentMetric.read(Path("alignments.tsv")):
            print(metric.read_name, metric.mapping_quality)
        ```
    """

    @classmethod
    def read(cls, path: Path, delimiter: str = "\t") -> Iterator[Self]:
        r"""
        Yield validated ``Metric`` instances from a delimited text file.

        Each non-header row is passed to :meth:`pydantic.BaseModel.model_validate` as a
        ``dict``, so all registered validators (empty-field coercion, list splitting, counter
        collection) run automatically.

        Args:
            path: Path to the delimited file. The first row must be a header containing
                column names that match the model's field names.
            delimiter: The field separator character. Defaults to ``"\\t"`` (TSV).

        Yields:
            One validated instance of this ``Metric`` subclass per data row.

        Note:
            The file is opened with ``encoding="utf-8-sig"`` to automatically strip a
            UTF-8 BOM (byte-order mark) from the header line, which some tools emit.

        Note:
            ``DictReader`` is intentionally called *without* an explicit ``fieldnames``
            argument so that any missing or unexpected columns are surfaced by pydantic's
            validation rather than silently ignored.

        Example:
            ```python
            for m in AlignmentMetric.read(Path("out.tsv")):
                print(m.read_name, m.mapping_quality)
            ```
        """
        # utf-8-sig encoding strips a leading BOM that some tools write to UTF-8 files.
        with path.open(encoding="utf-8-sig") as fin:
            for record in DictReader(fin, delimiter=delimiter):
                yield cls.model_validate(record)

    # This validator runs in ``"before"`` mode, meaning it executes *before* any field-level
    # validators (including ``DelimitedList._split_lists``). The ordering matters:
    #
    #   - ``list[T] | None``: this validator converts ``""`` → ``None`` first, so
    #     ``_split_lists`` never sees the empty string and correctly yields ``None``.
    #   - ``list[T]``: ``""`` passes through here unchanged (the field is not optional),
    #     then ``_split_lists`` converts ``""`` → ``[]``.
    #   - Any other optional field: ``""`` → ``None`` before pydantic type-coercion.
    @model_validator(mode="before")
    @classmethod
    def _empty_field_to_none(cls, data: Any) -> Any:
        """
        Convert empty strings to ``None`` for optional fields before validation.

        Runs in ``"before"`` mode so the raw input dict is available before any type
        coercion or field validators run.

        **Short-circuit conditions** (data returned unchanged):

        * *data* is not a ``dict`` (e.g. a model instance is being re-validated).
        * A field is not declared on the model — unknown keys are left for pydantic to
          handle (it will either ignore or reject them based on the model config).
        * A field's value is not the empty string.
        * A field is not annotated as optional — empty strings in non-optional fields
          are intentionally left for pydantic to reject with a validation error.

        Args:
            data: The raw input, typically a ``dict[str, str]`` from ``DictReader``.

        Returns:
            A new dict with ``""`` replaced by ``None`` for optional fields.
        """
        if not isinstance(data, dict):
            return data

        # Shallow-copy to avoid mutating the caller's dict, consistent with
        # ``CounterPivotTable._collect_counter_values``.
        data = dict(data)

        for field, value in data.items():
            info = cls.model_fields.get(field)
            if info is None:
                # Unknown field — leave it for pydantic to validate or ignore.
                continue
            if value == "" and is_optional(info.annotation):
                data[field] = None

        return data

    @classmethod
    def _header_fieldnames(cls) -> list[str]:
        """
        Return the column names to use as the header row when writing metrics to a file.

        Used by ``MetricWriter`` to configure the underlying ``csv.DictWriter``. For most
        models this is simply the declared field names, but when a ``Counter[StrEnum]``
        field is present the counter field is replaced by one column per enum member (using
        each member's string value), mirroring how the counter is pivoted during
        serialization.

        Returns:
            Ordered list of column name strings for the output header.

        Note:
            This method is intentionally **not** used during reading. ``read()`` passes no
            ``fieldnames`` to ``DictReader`` so that column discovery and any
            missing/unexpected-field errors are delegated to pydantic's validation.

        Todo:
            Support returning the correct set of fields when the model defines a custom
            ``model_serializer`` that adds or renames output keys.

        Example:
            Given a model with ``name: str`` and ``counts: Counter[Color]`` where
            ``Color`` has members ``RED``, ``GREEN``, ``BLUE``::

                cls._header_fieldnames()
                # → ["name", "red", "green", "blue"]
        """
        fieldnames: list[str] = list(cls.model_fields.keys())

        if cls._counter_fieldname is None:
            return fieldnames

        # Swap the Counter field for one column per enum member.
        fieldnames = [f for f in fieldnames if f != cls._counter_fieldname]

        # always set when _counter_fieldname is not None
        assert cls._counter_enum is not None
        fieldnames += [member.value for member in cls._counter_enum]

        return fieldnames
