from typing import Any


def envelope[T](data: T, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the stable success response shape."""
    return {"data": data, "meta": meta or {}, "error": None}
