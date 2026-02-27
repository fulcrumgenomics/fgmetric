from operator import or_
from functools import reduce
from collections import Counter
from types import GenericAlias, NoneType, UnionType
from typing import Union, cast, get_args, get_origin

type TypeAnnotation = type | UnionType | GenericAlias
"""
Represents any valid runtime type annotation handled by this module.

A type annotation is exactly one of:

1. ``type`` — a plain Python type, built-in or user-defined::

       int
       str
       MyClass

2. ``types.UnionType`` — a union declared with PEP 604 ``|`` syntax::

       int | str
       int | None
       int | str | None

3. ``types.GenericAlias`` — a parameterized generic declared with PEP 585 ``[]`` syntax::

       list[int]
       dict[str, int]
       Counter[str]

Note:
    ``typing`` special forms such as ``Optional[T]``, ``Union[T, U]``, and ``List[T]`` are
    *not* included in this alias because they are not instances of any of the three types
    above — they are ``typing._SpecialForm`` or ``typing._GenericAlias`` objects. This module
    normalises inputs that use those forms (e.g. via ``get_origin`` / ``get_args``) so callers
    do not need to handle them separately.
"""

# Used for ``isinstance`` checks throughout this module to narrow ``TypeAnnotation`` values.
TYPE_ANNOTATION_TYPES = (type, UnionType, GenericAlias)


def is_optional(annotation: TypeAnnotation | None) -> bool:
    """
    Return ``True`` if *annotation* is a union type that includes ``None``.

    All optional syntaxes are recognised — they are semantically identical at runtime:

    ===========================  =============================================
    Syntax                       Example
    ===========================  =============================================
    ``Optional[T]``              ``Optional[int]``
    ``Union[T, None]``           ``Union[int, None]``
    ``T | None`` (PEP 604)       ``int | None``
    Higher-arity with ``None``   ``int | str | None``
    ===========================  =============================================

    Args:
        annotation: A type annotation to inspect, or ``None``.

    Returns:
        ``True`` if *annotation* is a union whose members include ``NoneType``.
        ``False`` in all other cases, including when *annotation* is ``None`` itself.

    Examples:
        >>> is_optional(int | None)
        True
        >>> is_optional(int | str | None)
        True
        >>> is_optional(int)
        False
        >>> is_optional(list[int])
        False
        >>> is_optional(None)
        False
    """
    if annotation is None:
        return False

    origin = get_origin(annotation)
    args = get_args(annotation)

    # ``Optional[T]`` and ``Union[T, None]`` both have ``typing.Union`` as their origin.
    # ``T | None`` written with PEP 604 syntax has ``types.UnionType`` as its origin.
    # Both are unions, but they are distinct objects, so we check for either.
    return origin is not None and origin in (Union, UnionType) and NoneType in args


def unpack_optional(annotation: TypeAnnotation) -> TypeAnnotation:
    """
    Return the non-``None`` type(s) from an optional type annotation.

    Strips ``NoneType`` from a union, returning whatever remains:

    * Single remaining type → returned directly as that type.
    * Multiple remaining types → reconstructed as a ``types.UnionType`` via ``|``.

    The result is always a ``type``, ``GenericAlias``, or ``UnionType``. It is never a
    ``typing`` special form, because multi-type remainders are rebuilt using
    ``reduce(or_, args)`` (the ``|`` operator), which produces a native ``types.UnionType``
    rather than the ``typing._UnionGenericAlias`` that ``Union[*args]`` would create.

    Args:
        annotation: An optional type annotation (must satisfy :func:`is_optional`).

    Returns:
        The annotation with ``NoneType`` removed.

    Raises:
        ValueError: If *annotation* is not optional (i.e. :func:`is_optional` returns ``False``).

    Examples:
        >>> unpack_optional(int | None)
        <class 'int'>
        >>> unpack_optional(int | str | None)
        int | str
        >>> unpack_optional(list[int] | None)
        list[int]
        >>> unpack_optional(int)  # not optional
        ValueError: Type is not Optional: <class 'int'>
    """
    if not is_optional(annotation):
        raise ValueError(f"Type is not Optional: {annotation}")

    # Remove NoneType, keeping all other members.
    args = tuple(t for t in get_args(annotation) if t is not NoneType)

    if len(args) == 1:
        # Simple case: only one non-None type remains (e.g. ``int | None`` -> ``int``).
        type_parameter = args[0]
        # type narrowing
        assert isinstance(type_parameter, TYPE_ANNOTATION_TYPES)
        return type_parameter

    # Complex case: multiple non-None types remain (e.g. ``int | str | None`` -> ``int | str``).
    # ``reduce(or_, args)`` applies the ``|`` operator pairwise, producing a ``types.UnionType``.
    # This is preferable to ``Union[args]``, which would produce a ``typing._UnionGenericAlias``.
    return cast(UnionType, reduce(or_, args))


def has_optional_elements(annotation: TypeAnnotation | None) -> bool:
    """
    Return ``True`` if *annotation* is a ``list`` whose element type includes ``None``.

    This distinguishes between an *optional list field* (the list itself may be absent) and a
    *list with optional elements* (individual elements inside the list may be ``None``):

    ===============================  =======  ================================================
    Annotation                       Result   Reason
    ===============================  =======  ================================================
    ``list[int | None]``             ``True`` Elements are optional
    ``list[int | None] | None``      ``True`` Optional list; elements are still optional
    ``list[int]``                    ``False`` Elements are not optional
    ``list[int] | None``             ``False`` Optional list, but elements are not optional
    ``int | None``                   ``False`` Not a list at all
    ``None``                         ``False`` No annotation provided
    ===============================  =======  ================================================

    Args:
        annotation: A type annotation to inspect, or ``None``.

    Returns:
        ``True`` if the list element type is a union that includes ``NoneType``.
        ``False`` otherwise.

    Examples:
        >>> has_optional_elements(list[int | None])
        True
        >>> has_optional_elements(list[int | None] | None)
        True
        >>> has_optional_elements(list[int])
        False
        >>> has_optional_elements(list[int] | None)
        False
    """
    if annotation is None:
        return False

    # Unwrap an optional list field first, so ``list[T | None] | None`` is treated the same
    # as ``list[T | None]`` in the checks that follow.
    if is_optional(annotation):
        annotation = unpack_optional(annotation)

    if not is_list(annotation):
        return False

    args = get_args(annotation)
    # A well-formed ``list[T]`` has exactly one type argument; guard against bare ``list``.
    return len(args) == 1 and is_optional(args[0])


def has_origin(annotation: TypeAnnotation | None, origin: type) -> bool:
    """
    Return ``True`` if *annotation* is a parameterized generic of *origin*.

    Handles both plain and optional (``T | None``) forms, so callers do not need to
    unwrap optionals themselves:

    ========================  ==============  ========
    Annotation                origin          Result
    ========================  ==============  ========
    ``list[int]``             ``list``        ``True``
    ``list[int] | None``      ``list``        ``True``
    ``Counter[str]``          ``Counter``     ``True``
    ``Counter[str] | None``   ``Counter``     ``True``
    ``set[int]``              ``list``        ``False``
    ``int``                   ``list``        ``False``
    ========================  ==============  ========

    Args:
        annotation: A type annotation to inspect, or ``None``.
        origin: The generic type to match against (e.g. ``list``, ``set``, ``Counter``).

    Returns:
        ``True`` if ``get_origin(annotation)`` (after optionally unwrapping ``None``) is
        *origin*. ``False`` otherwise, including when *annotation* is ``None``.

    Examples:
        >>> has_origin(list[int], list)
        True
        >>> has_origin(list[int] | None, list)
        True
        >>> has_origin(set[int], list)
        False
    """
    if annotation is None:
        return False

    # Direct match: e.g. ``list[int]`` -> ``get_origin`` returns ``list``.
    if get_origin(annotation) is origin:
        return True

    # Optional match: e.g. ``list[int] | None`` -> unwrap, then check the inner type.
    if is_optional(annotation) and get_origin(unpack_optional(annotation)) is origin:
        return True

    return False


def is_list(annotation: TypeAnnotation | None) -> bool:
    """
    Return ``True`` if *annotation* is a parameterized ``list`` type.

    Matches plain and optional forms:

    =====================   ========
    Annotation              Result
    =====================   ========
    ``list[T]``             ``True``
    ``list[T] | None``      ``True``
    ``Optional[list[T]]``   ``True``
    ``list`` (bare)         ``False``
    ``set[T]``              ``False``
    ``None``                ``False``
    =====================   ========

    Args:
        annotation: A type annotation to inspect, or ``None``.

    Examples:
        >>> is_list(list[int])
        True
        >>> is_list(list[int] | None)
        True
        >>> is_list(set[int])
        False
        >>> is_list(list)  # bare list, no type parameter
        False
    """
    return has_origin(annotation, list)


def is_counter(annotation: TypeAnnotation | None) -> bool:
    """
    Return ``True`` if *annotation* is a parameterized ``Counter`` type.

    Matches plain and optional forms:

    =======================   ========
    Annotation                Result
    =======================   ========
    ``Counter[T]``            ``True``
    ``Counter[T] | None``     ``True``
    ``Optional[Counter[T]]``  ``True``
    ``Counter`` (bare)        ``False``
    ``dict[T, int]``          ``False``
    ``None``                  ``False``
    =======================   ========

    Args:
        annotation: A type annotation to inspect, or ``None``.

    Examples:
        >>> is_counter(Counter[str])
        True
        >>> is_counter(Counter[str] | None)
        True
        >>> is_counter(dict[str, int])
        False
        >>> is_counter(Counter)  # bare Counter, no type parameter
        False
    """
    return has_origin(annotation, Counter)
