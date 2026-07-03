"""Uvicorn entry point for the JaneAI backend."""

from __future__ import annotations

import logging
import sys

import uvicorn

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
        )
    except OSError as exc:
        logger.error(
            "Failed to start backend on %s:%s — %s",
            settings.api_host,
            settings.api_port,
            exc,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
