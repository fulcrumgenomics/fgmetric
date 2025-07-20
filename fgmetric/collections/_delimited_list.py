from enum import StrEnum
from typing import Any
from typing import ClassVar
from typing import TypeAlias
from typing import final
from typing import get_args

from pydantic import BaseModel
from pydantic import FieldSerializationInfo
from pydantic import SerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import ValidationInfo
from pydantic import field_serializer
from pydantic import field_validator
from pydantic import model_serializer
from pydantic import model_validator
from pydantic.fields import FieldInfo

from fgmetric._typing_extensions import has_optional_elements
from fgmetric._typing_extensions import is_counter
from fgmetric._typing_extensions import is_list

Fieldname: TypeAlias = str
"""A pydantic model field's name."""


# NB: Inheriting from BaseModel is necessary to declare field/model validators on the mixin, and
# for the class-level validations defined in `__pydantic_init_subclass__` to work.
class DelimitedList(BaseModel):
    """
    Serialize and deserialize delimited lists of (de)serializable types.

    When this mixin is added to `Metric`, fields annotated as `list[T]` will be read and written as
    comma-delimited strings. During validation, a comma-delimited string will be split into a list
    and its elements validated as instances of `T`. During serialization, the list elements will be
    serialized to string and then joined into a comma-delimited string.

    The list type `T` may be any serializable type. The field may be annotated as `list[T]` or
    `list[T] | None` - as with any primitive type, `None` will be validated from and serialized to
    the empty string.

    The delimiter may be configured by specifying the `collection_delimiter` class variable when
    declaring a model.

    Note:
        Roundtrips are lossy if list elements contain the delimiter character. For example, with the
        default comma delimiter, `["a,b", "c"]` serializes to `"a,b,c"` and deserializes back to
        `["a", "b", "c"]`. Avoid using delimiters that may appear in element values.

    Examples:
        Basic usage with comma delimiter (default):

        ```python
        class MyMetric(Metric):
            tags: list[int]  # "1,2,3" becomes [1, 2, 3]
        ```

        Custom delimiter:

        ```python
        class MyMetric(Metric):
            collection_delimiter = ";"
            tags: list[int]  # "1;2;3" becomes [1, 2, 3]
        ```

        Optional list field:

        ```python
        class MyMetric(Metric):
            tags: list[int] | None  # "" becomes None
        ```

        List field with Optional elements:

        ```python
        class MyMetric(Metric):
            tags: list[int | None]  # "1,,3" becomes [1, None, 3]
        ```
    """

    collection_delimiter: ClassVar[str] = ","
    _list_fieldnames: ClassVar[set[str]]
    _optional_element_fieldnames: ClassVar[set[str]]

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """
        Validations of the user-defined model.

        1. The collection delimiter must be a single character.
        2. The names of all fields annotated as `list[T]` or `list[T] | None` are stored in the
           private `_list_fieldnames` class variable.
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
        """Require collection delimiters to be single characters."""
        if len(cls.collection_delimiter) != 1:
            raise ValueError(
                f"Class collection delimiter must be a single character: {cls.collection_delimiter}"
            )

    @final
    @field_validator("*", mode="before")
    @classmethod
    def _split_lists(cls, value: Any, info: ValidationInfo) -> Any:
        """Split any fields annotated as `list[T]` on a comma delimiter."""
        if isinstance(value, str) and cls._is_list_field(info.field_name):
            if value:
                value = value.split(cls.collection_delimiter)

                # Convert empty strings to None for list[T | None] fields
                if info.field_name in cls._optional_element_fieldnames:
                    value = [None if el == "" else el for el in value]

            else:
                value = []

        return value

    @final
    @field_serializer("*", mode="wrap")
    def _join_lists(
        self,
        value: Any,
        nxt: SerializerFunctionWrapHandler,  # noqa: ARG002
        info: FieldSerializationInfo,
    ) -> Any:
        """Join any fields annotated as `list[T]` with a delimiter."""
        if isinstance(value, list) and self._is_list_field(info.field_name):
            # Let the default serializer handle each item first. This should return a list of
            # serialized values, applying default serialization to each list element.
            serialized_value = nxt(value)

            if isinstance(serialized_value, list):
                # If the handler returned a list, join it. (This is the expected branch.)
                # Also serialize `None` back to empty string.
                elements = ["" if item is None else str(item) for item in serialized_value]
                return self.collection_delimiter.join(elements)
            else:
                # If the handler already serialized to something else (unlikely), return as-is.
                return serialized_value

        return nxt(value)

    @final
    @classmethod
    def _is_list_field(cls, field_name: str | None) -> bool:
        """True if the field is annotated as `list[T]` on the class model."""
        return field_name is not None and field_name in cls._list_fieldnames


class CounterPivotTable(BaseModel):
    """
    A mixin to support pivot table representations of Counters.

    When this mixin is added to `Metric`, a field may be annotated as `Counter[T]`, and will be
    handled specially.

    This mixin permits only *one* field to be annotated as `Counter[T]`, and `T` must be a `StrEnum`
    type.

    During validation, fields in the input which match members of the enum type will be collected
    and included in a `Counter` on the validated model. If any members of the enum type are not
    found as fields in the input, they will be included with a count of 0 in the collected
    `Counter`.

    During serialization, the values of the associated `Counter` will be pivoted out, with one field
    in the output for each member of the enum type.

    **IMPORTANT:** As with all Python mixins, this class must precede `Metric` when declaring a
    *metric's parent classes, in order for its methods to take precedence over `Metric`'s defaults.
    """

    _counter_fieldname: ClassVar[str | None]
    _counter_enum: ClassVar[type[StrEnum] | None]

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)

        cls._counter_fieldname = cls._get_counter_fieldname()
        cls._counter_enum = cls._get_counter_enum()

    @final
    @classmethod
    def _get_counter_fieldname(cls) -> str | None:
        """
        Get and validate the name of a Counter field, if one is defined.

        Models using this mixin may define at most one Counter.

        Returns:
            The name of the single field annotated as `Counter[T]`.
            `None` if no fields are annotated as a `Counter`.

        Raises:
            TypeError: If the user-specified model includes more than one field annotated as
                `Counter[T]`.
        """
        counter_fieldnames = [
            name for name, info in cls.model_fields.items() if is_counter(info.annotation)
        ]

        if len(counter_fieldnames) > 1:
            # TODO permit multiple Counters, but require their values to be non-overlapping.
            raise TypeError("Only one Counter per model is currently supported.")

        return counter_fieldnames[0] if counter_fieldnames else None

    @final
    @classmethod
    def _get_counter_enum(cls) -> type[StrEnum] | None:  # noqa: C901
        """
        Get and validate the enum type parameter of a Counter field, if one is defined.

        Counter pivot tables are only supported for Counters of StrEnum.

        Returns:
            The type parameter of the single field annotated as `Counter[T]`.
            `None` if no fields are annotated as a `Counter`.

        Raises:
            TypeError: If the user-specified model includes a Counter field with a type parameter
                that is not a subclass of `StrEnum`.
        """
        if cls._counter_fieldname is None:
            # No counter fields -> short-circuit
            return None

        info: FieldInfo = cls.model_fields[cls._counter_fieldname]

        args = get_args(info.annotation)
        if len(args) == 1 and issubclass(args[0], StrEnum):
            enum_cls: type[StrEnum] = args[0]
        else:
            raise TypeError(
                f"Counter fields must have a StrEnum type parameter: {cls._counter_fieldname}"
            )

        return enum_cls

    @final
    @model_validator(mode="before")
    @classmethod
    def _collect_counter_values(cls, data: Any) -> Any:  # noqa: C901
        """Roll up Counters."""
        if not isinstance(data, dict):
            # Short circuit if we don't have a dictionary
            return data

        if cls._counter_fieldname is None:
            # Short circuit if we don't have a Counter field
            return data

        if cls._counter_fieldname in data:
            # Short circuit if a field with our Counter's fieldname already exists.
            # Either it's a dict representation of the Counter, and pydantic will coerce it to
            # Counter for us, or it's something else, and pydantic will reject it for us.
            return data

        # Initialize all members of the enum to zero, in case any members are absent from the input.
        assert cls._counter_enum is not None  # this is not None iff counter_fieldname is not None
        counts = {member: 0 for member in list(cls._counter_enum)}

        # Add counts found in the input. Any fields that correspond to an enum member are removed
        # from `data`
        keys_to_pop = []
        for key, value in data.items():
            if key in cls.model_fields:
                # Skip fields that are modeled explicitly
                continue

            try:
                member = cls._counter_enum(key)
                counts[member] = value
                keys_to_pop.append(key)
            except ValueError:
                # Let pydantic handle any other validation issues, or omit unmodeled fields
                continue

        for key in keys_to_pop:
            data.pop(key)

        data[cls._counter_fieldname] = counts

        return data

    @final
    @model_serializer(mode="wrap")
    def _pivot_counter_values(
        self,
        nxt: SerializerFunctionWrapHandler,  # noqa: ARG002
        info: SerializationInfo,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Pivot the Counter values out wide."""
        # Call the default serializer
        data: dict[str, Any] = nxt(self)

        if self._counter_fieldname is None:
            # Short circuit if we don't have a Counter field
            return data

        # Replace the counter field with keys for each of its enum's members
        counts = data.pop(self._counter_fieldname)
        for key, count in counts.items():
            data[key.value] = count

        return data
