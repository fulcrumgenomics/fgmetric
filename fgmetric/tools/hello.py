def hello(
    *,
    name: str = "World",
) -> None:
    """
    Print a greeting.

    Args:
        name: The person to greet.
    """
    print(f"Hello, {name}!")
