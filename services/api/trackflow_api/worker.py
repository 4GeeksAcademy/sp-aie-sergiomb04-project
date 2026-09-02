"""CLI entrypoint to launch Celery worker."""

from __future__ import annotations

import sys
from trackflow_api.celery_app import celery_app


def main() -> None:
    argv = [
        "worker",
        "--loglevel=info",
    ]
    if len(sys.argv) > 1:
        argv.extend(sys.argv[1:])
    celery_app.worker_main(argv=argv)


if __name__ == "__main__":
    main()
