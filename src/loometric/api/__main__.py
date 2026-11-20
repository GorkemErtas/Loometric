"""Supported local startup: one loopback worker, no proxy trust or request logging."""

import sys


def main() -> int:
    from loometric.api.settings import settings_from_environment

    try:
        settings = settings_from_environment()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    import uvicorn

    from loometric.api.app import create_app

    uvicorn.run(
        create_app(settings),
        host="127.0.0.1",
        port=settings.port,
        workers=1,
        reload=False,
        proxy_headers=False,
        access_log=False,
        server_header=False,
        limit_concurrency=32,
        backlog=32,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=10,
        h11_max_incomplete_event_size=16384,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
