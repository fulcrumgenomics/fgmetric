from typing import Optional
from typing import Union

import pytest

from fgmetric._typing_extensions import TypeAnnotation
from fgmetric._typing_extensions import is_list
from fgmetric._typing_extensions import is_optional
from fgmetric._typing_extensions import unpack_optional


@pytest.mark.parametrize(
    "annotation",
    [
        Union[str, None],
        Optional[str],
        str | None,
        Union[str, int, None],
        str | int | None,
    ],
)
def test_is_optional(annotation: TypeAnnotation) -> None:
    """Should identify optional union types, including higher-arity unions."""
    assert is_optional(annotation)


@pytest.mark.parametrize(
    "annotation",
    [
        str,
        Union[str, int],
        str | int,
    ],
)
def test_is_not_optional(annotation: TypeAnnotation) -> None:
    """Should reject non-optional or non-union types."""
    assert not is_optional(annotation)


def test_unpack_optional() -> None:
    """Should retrieve the parameterized type."""
    assert unpack_optional(int | None) is int


def test_unpack_optional_higher_arity() -> None:
    """Should reconstruct a union from higher-arity optionals."""
    result = unpack_optional(str | int | None)
    # The result should be str | int (a UnionType)
    assert result == str | int


@pytest.mark.parametrize(
    "annotation",
    [
        list[int],
        list[str],
        Optional[list[str]],
        list[str] | None,
    ],
)
def test_is_list(annotation: TypeAnnotation) -> None:
    """Should identify lists, even within an Optional."""
    assert is_list(annotation)


@pytest.mark.parametrize(
    "annotation",
    [
        str,
        str | None,
    ],
)
def test_is_not_list(annotation: TypeAnnotation) -> None:
    """Should reject non-list types."""
    assert not is_list(annotation)
