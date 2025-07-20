from typing import Annotated
from typing import TypeVar

from pydantic import BeforeValidator
from pydantic import PlainSerializer

T = TypeVar("T", bound=int | float | str)


CommaDelimitedList = Annotated[
    list[T],
    BeforeValidator(lambda x: x.split(",") if isinstance(x, str) else x),
    PlainSerializer(lambda xs: ",".join([str(x) for x in xs]), return_type=str),
]
"""A comma-delimited list of int, float, or str."""
