from typing import Any
from typing import ClassVar
from typing import final

from pydantic import BaseModel
from pydantic import FieldSerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import ValidationInfo
from pydantic import field_serializer
from pydantic import field_validator

from fgmetric._typing_extensions import has_optional_elements
from fgmetric._typing_extensions import is_list

# PEP 695 ``type`` statement (Python 3.12+), replacing the deprecated ``TypeAlias`` from ``typing``.
type Fieldname = str
"""A pydantic model field's name."""

__all__ = ["DelimitedList", "Fieldname"]


# NB: Inheriting from BaseModel is necessary to declare field/model validators on the mixin, and
# for the class-level validations defined in ``__pydantic_init_subclass__`` to work.
class DelimitedList(BaseModel):
    """
    Mixin that serializes and deserializes ``list[T]`` fields as delimiter-separated strings.

    When added to a pydantic model, any field annotated as ``list[T]`` is automatically:

    * **Deserialized** — a delimited string is split on ``collection_delimiter`` and each
      segment is validated as ``T``.
    * **Serialized** — list elements are serialized individually (using pydantic's standard
      logic), then joined back into a single delimited string.

    The element type ``T`` may be any type that pydantic can serialize and deserialize (e.g.
    ``int``, ``float``, ``datetime``, nested models, etc.).

    **Field annotation forms**

    ============================  ======================  ==================================
    Annotation                    Empty string input      Non-empty string input
    ============================  ======================  ==================================
    ``list[T]``                   ``[]``                  ``["a", "b"]``
    ``list[T] | None``            ``None``                ``["a", "b"]``
    ``list[T | None]``            ``[]``                  ``["a", None, "b"]`` (on ``"a,,b"``)
    ============================  ======================  ==================================

    Note:
        **Round-trips are lossy** if element values contain the delimiter character. For example,
        with the default comma delimiter, ``["a,b", "c"]`` serializes to ``"a,b,c"`` and
        deserializes back to ``["a", "b", "c"]``. Choose a delimiter that cannot appear in
        element values.

    Note:
        ``collection_delimiter`` must differ from the enclosing file's field separator. For
        example, do **not** set ``collection_delimiter = "\\t"`` when writing TSV files — this
        causes silent data corruption because the list delimiter becomes indistinguishable from
        the column delimiter.

    Examples:
        Basic usage — comma delimiter (default):

        ```python
        class MyMetric(DelimitedList):
            tags: list[int]

        MyMetric(tags="1,2,3").tags        # → [1, 2, 3]
        MyMetric(tags=[1, 2, 3]).model_dump()  # → {"tags": "1,2,3"}
        ```

        Custom delimiter:

        ```python
        class MyMetric(DelimitedList):
            collection_delimiter = ";"
            tags: list[int]

        MyMetric(tags="1;2;3").tags        # → [1, 2, 3]
        MyMetric(tags=[1, 2, 3]).model_dump()  # → {"tags": "1;2;3"}
        ```

        Optional list field — the whole field may be absent:

        ```python
        class MyMetric(DelimitedList):
            tags: list[int] | None

        MyMetric(tags="").tags             # → None
        MyMetric(tags=None).model_dump()   # → {"tags": ""}
        ```

        List with optional elements — individual elements may be absent:

        ```python
        class MyMetric(DelimitedList):
            tags: list[int | None]

        MyMetric(tags="1,,3").tags         # → [1, None, 3]
        MyMetric(tags=[1, None, 3]).model_dump()  # → {"tags": "1,,3"}
        ```
    """

    # Override in a subclass to change the delimiter for all list fields on that model.
    collection_delimiter: ClassVar[str] = ","

    # Populated at subclass creation time by ``__pydantic_init_subclass__``.
    # Stored as class variables so that the per-field validator/serializer can do O(1) lookups
    # rather than inspecting annotations on every call.
    _list_fieldnames: ClassVar[set[str]]
    _optional_element_fieldnames: ClassVar[set[str]]

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """
        Validate the subclass definition and pre-compute field metadata at class-creation time.

        Called automatically by pydantic when a subclass of this mixin is defined.
        Performing these checks and caches here — rather than inside the validators — means
        the work is done once per class, not once per field value.

        Steps:

        1. Validate that ``collection_delimiter`` is exactly one character (raises
           ``ValueError`` immediately if not, so misconfigured models are caught at import
           time rather than at first use).
        2. Cache the names of all ``list[T]`` (and ``list[T] | None``) fields in
           ``_list_fieldnames`` for O(1) lookup in :meth:`_is_list_field`.
        3. Cache the names of all ``list[T | None]`` fields in
           ``_optional_element_fieldnames`` so that :meth:`_split_lists` knows which fields
           need empty-string-to-``None`` conversion.
        """
        super().__pydantic_init_subclass__(**kwargs)

        cls._require_single_character_collection_delimiter()
        cls._list_fieldnames = {
            name for name, info in cls.model_fields.items() if is_list(info.annotation)
        }
        cls._optional_element_fieldnames = {
            name
            for name, info in cls.model_fields.items()
            if has_optional_elements(info.annotation)
        }

    @classmethod
    def _require_single_character_collection_delimiter(cls) -> None:
        """
        Raise ``ValueError`` if ``collection_delimiter`` is not exactly one character.

        Enforced at class-creation time (inside ``__pydantic_init_subclass__``) so that a
        misconfigured model fails loudly at import time rather than silently producing
        malformed output at runtime.
        """
        if len(cls.collection_delimiter) != 1:
            raise ValueError(
                f"collection_delimiter must be a single character, got: {cls.collection_delimiter!r}"
            )

    @final
    @field_validator("*", mode="before")
    @classmethod
    def _split_lists(cls, value: Any, info: ValidationInfo) -> Any:
        """
        Split a delimiter-separated string into a list before pydantic validates the field.

        This validator runs in ``"before"`` mode, meaning it receives the raw input value
        *before* pydantic applies type coercion. Only fields in ``_list_fieldnames`` are
        affected; all other fields pass through unchanged.

        Deserialization rules:

        ==================  ========================  ====================================
        Input               Field annotation          Result
        ==================  ========================  ====================================
        ``""``              ``list[T]``               ``[]``
        ``""``              ``list[T] | None``        ``[]`` (pydantic coerces to ``None``)
        ``"a,b,c"``         ``list[T]``               ``["a", "b", "c"]`` (pre-coercion)
        ``"a,,c"``          ``list[T | None]``        ``["a", None, "c"]``
        non-string          any                       passed through unchanged
        ==================  ========================  ====================================

        Note:
            Non-string inputs (e.g. a list passed directly in Python) are returned as-is,
            allowing programmatic construction of model instances without going through the
            string-splitting path.
        """
        if isinstance(value, str) and cls._is_list_field(info.field_name):
            if value:
                value = value.split(cls.collection_delimiter)

                # For ``list[T | None]`` fields, map empty segments back to ``None`` so that
                # ``"a,,c"`` correctly produces ``["a", None, "c"]`` rather than ``["a", "", "c"]``.
                if info.field_name in cls._optional_element_fieldnames:
                    value = [None if el == "" else el for el in value]
            else:
                # An empty string represents an empty list, not a list with one empty element.
                value = []

        return value

    @final
    @field_serializer("*", mode="wrap")
    def _join_lists(
        self,
        value: Any,
        nxt: SerializerFunctionWrapHandler,
        info: FieldSerializationInfo,
    ) -> Any:
        """
        Join a list into a delimiter-separated string after pydantic serializes each element.

        This serializer runs in ``"wrap"`` mode: ``nxt`` is pydantic's default serializer,
        which is called first to serialize each list element individually (applying all
        standard pydantic logic — datetime formatting, nested model dumping, enum values,
        etc.). The resulting list of strings is then joined with ``collection_delimiter``.

        Only fields in ``_list_fieldnames`` are affected; all other fields are passed
        directly to ``nxt``.

        Serialization rules:

        =====================  =============================
        Input element value    Output segment
        =====================  =============================
        ``None``               ``""``  (empty segment)
        any serializable ``T`` ``str(serialized_value)``
        =====================  =============================

        Note:
            The ``None`` → ``""`` mapping is the exact inverse of the ``""`` → ``None``
            mapping in :meth:`_split_lists`, ensuring lossless round-trips for
            ``list[T | None]`` fields (provided elements do not contain the delimiter).
        """
        if isinstance(value, list) and self._is_list_field(info.field_name):
            # Delegate to pydantic's default serializer first so that each element is
            # serialized according to its own type (e.g. a ``datetime`` becomes an ISO string).
            serialized_value = nxt(value)

            if isinstance(serialized_value, list):
                # Expected path: map None → "" and join.
                elements = ["" if item is None else str(item) for item in serialized_value]
                return self.collection_delimiter.join(elements)

            # Unexpected: ``nxt`` already collapsed the list to a non-list (should not happen
            # with standard pydantic serializers, but guard against custom ones).
            return serialized_value

        return nxt(value)

    @final
    @classmethod
    def _is_list_field(cls, field_name: str | None) -> bool:
        """
        Return ``True`` if *field_name* refers to a ``list[T]`` field on this model.

        Uses the pre-computed ``_list_fieldnames`` set for O(1) lookup.
        Returns ``False`` for ``None`` (pydantic may pass ``None`` when the field name is
        unavailable, e.g. during root validation).
        """
        return field_name is not None and field_name in cls._list_fieldnames
