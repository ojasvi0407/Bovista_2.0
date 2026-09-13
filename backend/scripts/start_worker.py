"""Render worker entrypoint that assembles its least-privilege database URL."""

from scripts.database_url import ensure_database_url


def main() -> None:
    ensure_database_url()
    import asyncio

    from scripts.worker import run

    asyncio.run(run())


if __name__ == "__main__":
    main()
