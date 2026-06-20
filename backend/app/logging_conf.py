import logging
import sys


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_summary(logger: logging.Logger, counts: dict) -> None:
    """Log a structured per-run summary with extraction/export counts."""
    logger.info(
        "Run summary | extracted=%d unresolved_dropped=%d dedupe_collisions=%d written=%d",
        counts.get("extracted", 0),
        counts.get("unresolved_dropped", 0),
        counts.get("dedupe_collisions", 0),
        counts.get("written", 0),
    )
