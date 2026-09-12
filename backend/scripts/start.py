import os
from collections.abc import Mapping

import uvicorn


def server_config(environment: Mapping[str, str]) -> dict[str, object]:
    raw_port = environment.get("PORT", "10000")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError("PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535.")
    return {"app": "app.main:app", "host": "0.0.0.0", "port": port}  # noqa: S104


def main() -> None:
    uvicorn.run(**server_config(os.environ))


if __name__ == "__main__":
    main()
