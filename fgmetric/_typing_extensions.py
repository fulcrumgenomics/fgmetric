from functools import reduce
from operator import or_
from types import GenericAlias
from types import NoneType
from types import UnionType
from typing import Union
from typing import cast
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


def is_optional(annotation: TypeAnnotation | None) -> bool:
    """
    Check if a type is optional (i.e., a union containing `None`).

    An optional type may be declared using three syntaxes: `Optional[T]`, `Union[T, None]`, or
    `T | None`. Higher-arity unions are also supported (e.g., `T | U | None`).

    Args:
        annotation: A type annotation.

    Returns:
        True if the type is a union type containing `None`.
        False otherwise.
    """
    if annotation is None:
        return False

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Optional[T] and Union[T, None] have `typing.Union` as its origin.
    # PEP604 syntax (`T | None`) has `types.UnionType` as its origin.
    return origin is not None and (origin is Union or origin is UnionType) and NoneType in args


def unpack_optional(annotation: TypeAnnotation) -> TypeAnnotation:
    """
    Retrieve the non-None type(s) from an optional type annotation.

    For simple optionals like `T | None`, returns `T`.
    For higher-arity unions like `T | U | None`, returns `T | U`.

    Args:
        annotation: An optional type annotation.

    Returns:
        The type annotation with `None` removed.

    Raises:
        ValueError: If the input is not an optional type.
    """
    if not is_optional(annotation):
        raise ValueError(f"Type is not Optional: {annotation}")

    args = tuple(t for t in get_args(annotation) if t is not NoneType)

    if len(args) == 1:
        type_parameter = args[0]
        assert isinstance(type_parameter, TYPE_ANNOTATION_TYPES)  # type narrowing
        return type_parameter
    else:
        # Reconstruct a union from the remaining types
        # NB: applying `or_` to a sequence of type annotations will yield a `UnionType`.
        # NB: it is possible to construct a union using `Union[args]`, however this creates a typing
        # special form (`_UnionGenericAlias`) instead of a `UnionType`.
        return cast(UnionType, reduce(or_, args))


def has_origin(annotation: TypeAnnotation | None, origin: type) -> bool:
    """
    Check if a type annotation is a parameterized collection of the given type.

    Args:
        annotation: A type annotation.
        origin: The collection type to check for (e.g., `list`, `set`, `Counter`).

    Returns:
        True if the annotation is a parameterized instance of `origin`.
        False otherwise.
    """
    if annotation is None:
        return False
    elif get_origin(annotation) is origin:
        return True
    elif is_optional(annotation) and get_origin(unpack_optional(annotation)) is origin:
        return True
    else:
        return False


def is_list(annotation: TypeAnnotation | None) -> bool:
    """
    Check if a type annotation is a list type.

    Matches `list[T]`, `Optional[list[T]]`, and `list[T] | None`.
    """
    return has_origin(annotation, list)
