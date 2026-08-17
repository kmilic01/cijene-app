"""Safe, idempotent daily database refresh entry point."""

import argparse
import logging
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from downloader import download_archive, list_archives, newest_archive, validate_and_extract_zip
from import_data import CompletenessThresholds, replace_snapshot, validate_dataset

LOG = logging.getLogger("cijene.refresh")


def current_snapshot_date(database_url: str) -> date | None:
    connection = psycopg2.connect(database_url)
    try:
        connection.set_session(readonly=True, autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT import_date FROM prices LIMIT 1")
            row = cursor.fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    if row[0] is None:
        raise RuntimeError("Current database snapshot has a NULL import_date")
    return row[0]


def _positive_environment_integer(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {raw_value!r}") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero, got {value}")
    return value


def completeness_thresholds() -> CompletenessThresholds:
    return CompletenessThresholds(
        chains=_positive_environment_integer("REFRESH_MIN_CHAINS", 20),
        stores=_positive_environment_integer("REFRESH_MIN_STORES", 700),
        products=_positive_environment_integer("REFRESH_MIN_PRODUCTS", 250_000),
        prices=_positive_environment_integer("REFRESH_MIN_PRICES", 8_000_000),
    )


def run(discovery_only: bool = False) -> int:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    current = current_snapshot_date(database_url)
    LOG.info("Current database date: %s", current or "empty database")
    candidate = newest_archive(list_archives())
    LOG.info("Newest available archive date: %s", candidate.date)
    LOG.info("Archive URL: %s", candidate.url)
    LOG.info(
        "Expected archive size: %s",
        f"{candidate.size} bytes" if candidate.size is not None else "not supplied",
    )
    update_required = current is None or candidate.date > current
    LOG.info("Update required: %s", "yes" if update_required else "no")
    if discovery_only:
        LOG.info("Discovery-only result: success; no download or database write performed")
        return 0
    if current is not None and candidate.date <= current:
        LOG.info("Update needed: no")
        LOG.info("Final status: no newer archive")
        return 0
    LOG.info("Update needed: yes")
    with tempfile.TemporaryDirectory(prefix="cijene-refresh-") as temporary:
        root = Path(temporary)
        archive_path = download_archive(candidate, root)
        LOG.info("Download result: downloaded %s (%d bytes)", archive_path.name, archive_path.stat().st_size)
        extracted = root / "extracted"
        validate_and_extract_zip(archive_path, extracted)
        minimums = completeness_thresholds()
        LOG.info(
            "Configured completeness minimums: chains=%d stores=%d products=%d prices=%d",
            minimums.chains, minimums.stores, minimums.products, minimums.prices,
        )
        validation = validate_dataset(extracted, minimums)
        LOG.info("Validation result: valid; chains=%d stores=%d products=%d prices=%d",
                 len(validation.chains), validation.stores, validation.products, validation.prices)
        connection = psycopg2.connect(database_url)
        try:
            result = replace_snapshot(
                connection, validation, candidate.date,
                os.getenv("REFRESH_LOCK_TIMEOUT", "30s"),
                os.getenv("REFRESH_STATEMENT_TIMEOUT", "6h"),
            )
        finally:
            connection.close()
        if result.skipped:
            LOG.info("A concurrent refresh already installed this archive")
            LOG.info("Final status: no newer archive")
            return 0
        LOG.info("Imported chain count: %d", result.chains)
        LOG.info("Imported row counts: stores=%d products=%d prices=%d",
                 result.stores, result.products, result.prices)
        LOG.info("Database replacement duration: %.1f seconds", result.duration_seconds)
        LOG.info("Final status: updated")
        return 0


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument(
            "--discovery-only",
            action="store_true",
            help="Read dates and archive metadata without downloading or writing",
        )
        arguments = parser.parse_args()
        return run(discovery_only=arguments.discovery_only)
    except Exception:
        LOG.exception("Final status: failed while preserving old data")
        return 1


if __name__ == "__main__":
    sys.exit(main())
