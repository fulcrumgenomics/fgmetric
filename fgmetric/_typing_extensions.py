from types import GenericAlias
from types import NoneType
from types import UnionType
from typing import Union
from typing import get_args
from typing import get_origin

type TypeAnnotation = type | UnionType | GenericAlias
"""
A type annotation may be any of the following:
    1) `type`, when declaring any of the built-in Python types
    2) `types.UnionType`, when declaring union types using PEP604 syntax (e.g. `int | None`)
    3) `types.GenericAlias`, when declaring generic collection types using PEP 585 syntax (e.g.
       `list[int]`)
"""

TYPE_ANNOTATION_TYPES = (type, UnionType, GenericAlias)


def is_optional(annotation: TypeAnnotation) -> bool:
    """
    Check if a type is `Optional`.

    An optional type may be declared using three syntaxes: `Optional[T]`, `Union[T, None]`, or
    `T | None`. All of these syntaxes are supported by this function.

    For simplicity, this function does not permit `T` to be a union type.

    Args:
        annotation: A type annotation.

    Returns:
        True if the type is a union type with exactly two elements, one of which is `None`.
        False otherwise.

    Raises:
        TypeError: If the input is not a valid `TypeAnnotation` type.
    """
    origin = get_origin(annotation)
    args = get_args(annotation)

    # Optional[T] and Union[T, None] have `typing.Union` as its origin.
    # PEP604 syntax (`T | None`) has `types.UnionType` as its origin.
    return (
        origin is not None
        and (origin is Union or origin is UnionType)
        and len(args) == 2
        and NoneType in args
    )


def unpack_optional(annotation: TypeAnnotation) -> TypeAnnotation:
    """Retrieve the parameterized type of the Optional."""
    if not is_optional(annotation):
        raise ValueError(f"Type is not Optional: {annotation}")

    args = [t for t in get_args(annotation) if t is not NoneType]
    type_parameter = args[0]

    assert isinstance(type_parameter, TYPE_ANNOTATION_TYPES)  # type narrowing

    return type_parameter


def is_list(annotation: TypeAnnotation | None) -> bool:
    """True if the type annotation is not None and a list type."""
    if annotation is None:
        return False
    elif get_origin(annotation) is list:
        return True
    elif is_optional(annotation) and get_origin(unpack_optional(annotation)) is list:
        return True
    else:
        return False
