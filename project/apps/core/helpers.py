def python_weekday_to_django_weekday(python_weekday: int) -> int:
    """Convert Python weekday (0=Mon, 6=Sun) to Django weekday (2=Mon, 7=Sat, 1=Sun)."""

    return python_weekday + 2 if python_weekday != 6 else 1
