from __future__ import annotations

import logging
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogRecordFields:
    timestamp: str = "%(asctime)s"
    level: str = "%(levelname)s"
    logger: str = "%(name)s"
    message: str = "%(message)s"


def configure_logging(settings: object) -> None:
    level_name = getattr(settings, "level", "INFO")
    level = logging.getLevelName(str(level_name).upper())
    if not isinstance(level, int):
        level = logging.INFO

    fields = LogRecordFields()
    formatter = logging.Formatter(
        fmt=f"{fields.timestamp} | {fields.level:<8} | {fields.logger} | {fields.message}",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
