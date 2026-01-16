from typing import Any
from typing import ClassVar
from typing import final

from pydantic import BaseModel
from pydantic import FieldSerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import ValidationInfo
from pydantic import field_serializer
from pydantic import field_validator

from fgmetric._typing_extensions import is_list


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

    The delimiter may be configured by specifying the `list_delimiter` class variable when declaring
    a model.
    """

    collection_delimiter: ClassVar[str] = ","
    _list_fieldnames: ClassVar[set[str]]

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """
        Validations of the user-defined model.

        1. The list delimiter must be a single character.
        2. The names of all fields annotated as `list[T]` or `list[T] | None` are stored in the
           private `_list_fieldnames` class variable.
        """
        super().__pydantic_init_subclass__(**kwargs)

        cls._require_single_character_list_delimiter()
        cls._list_fieldnames = {
            name for name, info in cls.model_fields.items() if is_list(info.annotation)
        }

    @classmethod
    def _require_single_character_list_delimiter(cls) -> None:
        """Require list delimiters to be single characters."""
        if len(cls.list_delimiter) != 1:
            raise ValueError(
                f"Class list delimiter must be a single character: {cls.list_delimiter}"
            )

    @final
    @field_validator("*", mode="before")
    @classmethod
    def _split_lists(cls, value: Any, info: ValidationInfo) -> Any:
        """Split any fields annotated as `list[T]` on a comma delimiter."""
        if isinstance(value, str) and cls._is_list_field(info.field_name):
            value = value.split(cls.list_delimiter) if value else []

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
                return self.list_delimiter.join([str(item) for item in serialized_value])
            else:
                # If the handler already serialized to something else (unlikely), return as-is.
                return serialized_value

        return nxt(value)

    @final
    @classmethod
    def _is_list_field(cls, field_name: str | None) -> bool:
        """True if the field is annotated as `list[T]` on the class model."""
        return field_name is not None and field_name in cls._list_fieldnames
