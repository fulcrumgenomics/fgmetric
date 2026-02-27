from enum import StrEnum
from typing import Any, ClassVar, final, get_args

from pydantic.fields import FieldInfo
from pydantic import BaseModel, SerializationInfo, SerializerFunctionWrapHandler, model_serializer, model_validator

from fgmetric._typing_extensions import is_counter, is_optional


class CounterPivotTable(BaseModel):
    """
    Mixin that transparently pivots a ``Counter[StrEnum]`` field to and from wide-format columns.

    **Concept — pivot tables**

    A *pivot table* representation stores one value per enum member as its own column::

        # Wide format (CSV / TSV row)
        name,  red,  green,  blue
        foo,   10,   20,     30

    This mixin maps that wide representation to a single ``Counter[Color]`` field on the model::

        class MyMetric(CounterPivotTable, Metric):
            name: str
            counts: Counter[Color]   # absorbs the red/green/blue columns

    **Deserialization (wide → Counter)**

    When a row is validated, any key that matches a member of the enum type is removed from the
    raw input dict and accumulated into a ``Counter``.  Missing enum members default to ``0``.

    **Serialization (Counter → wide)**

    When a model is serialized, the ``Counter`` field is removed and each enum member is written
    back as its own key, using the enum's string value as the column name.

    **Constraints**

    * Exactly **zero or one** ``Counter[T]`` field is allowed per model.
    * The type parameter ``T`` must be a ``StrEnum`` subclass.
    * Optional counters (``Counter[T] | None``) are not supported.

    Note:
        As with all Python mixins, ``CounterPivotTable`` must appear **before** ``Metric`` in
        the parent-class list so that its ``model_validator`` and ``model_serializer`` take
        precedence over ``Metric``'s defaults::

            class MyMetric(CounterPivotTable, Metric): ...  # correct
            class MyMetric(Metric, CounterPivotTable): ...  # wrong — validators may not fire

    Examples:
        Defining a metric with a pivot-table counter:

        ```python
        class Color(StrEnum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"

        class MyMetric(CounterPivotTable, Metric):
            name: str
            counts: Counter[Color]
        ```

        Deserialization — wide columns are folded into the Counter:

        ```python
        row = {"name": "foo", "red": 10, "green": 20, "blue": 30}
        m = MyMetric.model_validate(row)
        m.counts  # → Counter({Color.RED: 10, Color.GREEN: 20, Color.BLUE: 30})
        ```

        Serialization — the Counter is pivoted back to wide columns:

        ```python
        m.model_dump()
        # → {"name": "foo", "red": 10, "green": 20, "blue": 30}
        ```

        Missing enum members default to zero:

        ```python
        row = {"name": "foo", "red": 5}
        m = MyMetric.model_validate(row)
        m.counts  # → Counter({Color.RED: 5, Color.GREEN: 0, Color.BLUE: 0})
        ```
    """

    # Both are ``None`` when no ``Counter[T]`` field is declared on the model.
    # Populated once at subclass-creation time by ``__pydantic_init_subclass__``.
    _counter_fieldname: ClassVar[str | None]
    _counter_enum: ClassVar[type[StrEnum] | None]

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """
        Validate the subclass definition and cache counter metadata at class-creation time.

        Called automatically by pydantic when a subclass is defined. Caching here means
        annotation inspection happens once per class rather than on every validate/serialize call.

        Steps:

        1. Locate and validate the ``Counter[T]`` field (at most one allowed).
        2. Extract and validate the enum type parameter ``T`` (must be a ``StrEnum`` subclass).
        """
        super().__pydantic_init_subclass__(**kwargs)

        cls._counter_fieldname = cls._get_counter_fieldname()
        cls._counter_enum = cls._get_counter_enum()

    @final
    @classmethod
    def _get_counter_fieldname(cls) -> str | None:
        """
        Return the name of the ``Counter[T]`` field, or ``None`` if no such field exists.

        Validates that the model defines **at most one** counter field, and that the counter
        is not optional (``Counter[T] | None`` is not supported).

        Returns:
            The field name string if exactly one ``Counter[T]`` field is present.
            ``None`` if no ``Counter[T]`` field is defined.

        Raises:
            TypeError: If more than one field is annotated as ``Counter[T]``.
            TypeError: If the counter field is annotated as optional (``Counter[T] | None``).

        Examples:
            >>> # One counter field → returns its name
            >>> class M(CounterPivotTable, Metric):
            ...     counts: Counter[Color]
            >>> M._counter_fieldname
            'counts'

            >>> # No counter field → returns None
            >>> class M(CounterPivotTable, Metric):
            ...     name: str
            >>> M._counter_fieldname
            None

            >>> # Two counter fields → raises TypeError
            >>> class M(CounterPivotTable, Metric):
            ...     counts_a: Counter[Color]
            ...     counts_b: Counter[Color]
            TypeError: Only one Counter per model is currently supported. ...
        """
        counter_fieldnames = [
            name for name, info in cls.model_fields.items() if is_counter(info.annotation)
        ]

        if len(counter_fieldnames) > 1:
            raise TypeError(
                "Only one Counter per model is currently supported. "
                f"Found multiple Counter fields: {', '.join(counter_fieldnames)}"
            )

        counter_fieldname: str | None = counter_fieldnames[0] if counter_fieldnames else None

        if counter_fieldname is not None:
            counter_field_info: FieldInfo = cls.model_fields[counter_fieldname]
            if is_optional(counter_field_info.annotation):
                raise TypeError(
                    f"Optional Counter fields are not supported: {counter_fieldname!r}"
                )

        return counter_fieldname

    @final
    @classmethod
    def _get_counter_enum(cls) -> type[StrEnum] | None:  # noqa: C901
        """
        Return the ``StrEnum`` type parameter of the counter field, or ``None`` if absent.

        Only ``Counter[T]`` where ``T`` is a ``StrEnum`` subclass is supported, because the enum's
        string values are used directly as column names during serialization.

        Returns:
            The ``StrEnum`` subclass used as the counter's type parameter.
            ``None`` if no ``Counter[T]`` field is defined on the model.

        Raises:
            TypeError: If the counter field's type parameter is not a ``StrEnum`` subclass.

        Examples:
            >>> class M(CounterPivotTable, Metric):
            ...     counts: Counter[Color]   # Color is a StrEnum
            >>> M._counter_enum
            <enum 'Color'>

            >>> class M(CounterPivotTable, Metric):
            ...     counts: Counter[int]     # int is not a StrEnum
            TypeError: Counter fields must have a StrEnum type parameter: ...
        """
        if cls._counter_fieldname is None:
            return None

        info: FieldInfo = cls.model_fields[cls._counter_fieldname]
        args = get_args(info.annotation)

        if len(args) == 1 and issubclass(args[0], StrEnum):
            enum_cls: type[StrEnum] = args[0]
            return enum_cls

        raise TypeError(
            f"Counter fields must have a StrEnum type parameter, "
            f"got {info.annotation!r} for field {cls._counter_fieldname!r}"
        )

    @final
    @model_validator(mode="before")
    @classmethod
    def _collect_counter_values(cls, data: Any) -> Any:  # noqa: C901
        """
        Fold wide-format enum columns from the raw input dict into a single ``Counter``.

        Runs in ``"before"`` mode so the raw input dict is available before pydantic applies
        any type coercion.

        **Short-circuit conditions** (data is returned unchanged):

        * *data* is not a ``dict`` (e.g. a model instance is being re-validated).
        * No ``Counter[T]`` field is defined on this model.
        * The counter's field name already exists as a key in *data* — either as a pre-built
          ``Counter`` / ``dict`` (pydantic will coerce it) or as an invalid value (pydantic
          will reject it).

        **Normal path**:

        1. Initialize all enum members to ``0`` so that missing columns default to zero.
        2. Scan *data* for keys that are valid enum values; accumulate their counts and remove
           the keys from *data* (they are not modelled as individual fields).
        3. Assign the assembled ``counts`` dict to ``data[counter_fieldname]``; pydantic will
           coerce it to a ``Counter`` during validation.

        Note:
            Keys that are both valid enum values *and* explicit model fields are treated as
            model fields and are **not** folded into the counter. This prevents accidental
            shadowing of real fields by enum members with the same name.
        """
        if not isinstance(data, dict):
            return data

        # Work on a shallow copy to avoid mutating the caller's dict.
        data = dict(data)

        if cls._counter_fieldname is None:
            return data

        if cls._counter_fieldname in data:
            # A counter value was supplied directly; let pydantic validate it.
            return data

        # ``_counter_enum`` is always set when ``_counter_fieldname`` is set.
        assert cls._counter_enum is not None

        # Seed all enum members at zero so that absent columns are represented, not omitted.
        counts: dict[StrEnum, Any] = {
            member: 0 for member in cls._counter_enum}

        # Collect enum-valued keys from the input, removing them so they don't confuse pydantic.
        keys_to_pop: list[str] = []
        for key, value in data.items():
            if key in cls.model_fields:
                # Explicit model fields take precedence over same-named enum members.
                continue
            try:
                member = cls._counter_enum(key)
                counts[member] = value
                keys_to_pop.append(key)
            except ValueError:
                # Not an enum member — leave it in data for pydantic to validate or ignore.
                continue

        for key in keys_to_pop:
            data.pop(key)

        data[cls._counter_fieldname] = counts
        return data

    @final
    @model_serializer(mode="wrap")
    def _pivot_counter_values(
        self,
        nxt: SerializerFunctionWrapHandler,
        info: SerializationInfo,  # noqa: ARG002
    ) -> dict[str, Any]:
        """
        Pivot the ``Counter`` field back to wide-format columns during serialization.

        Runs in ``"wrap"`` mode: ``nxt`` is called first to serialize the model using pydantic's
        default logic, producing a ``dict``. The counter field is then popped from that dict and
        replaced with one key per enum member, using each member's string value as the key.

        This is the exact inverse of :meth:`_collect_counter_values`.

        Note:
            ``info`` (the ``SerializationInfo`` context) is received but not used — it is
            accepted to satisfy the ``"wrap"`` serializer signature.

        Example:
            Given ``counts = Counter({Color.RED: 10, Color.GREEN: 20, Color.BLUE: 30})``,
            the output dict will contain ``{"red": 10, "green": 20, "blue": 30}`` in place
            of ``{"counts": Counter(...)}``.
        """
        data: dict[str, Any] = nxt(self)

        if self._counter_fieldname is None:
            return data

        # Pop the counter dict and write one key per enum member using the member's string value.
        counts = data.pop(self._counter_fieldname)
        for key, count in counts.items():
            data[key.value] = count

        return data
