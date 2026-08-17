"""Validate and atomically import one cijene.dev snapshot."""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import monotonic

STORE_HEADERS = ["store_id", "type", "address", "city", "zipcode"]
PRODUCT_HEADERS = ["product_id", "barcode", "name", "brand", "category", "unit", "quantity"]
PRICE_HEADERS = ["store_id", "product_id", "price", "unit_price", "best_price_30", "anchor_price", "special_price"]
LOG = logging.getLogger("cijene.refresh.validation")


@dataclass(frozen=True)
class ChainDataset:
    name: str
    path: Path
    stores: int
    products: int
    prices: int


@dataclass(frozen=True)
class DatasetValidation:
    chains: tuple[ChainDataset, ...]
    stores: int
    products: int
    prices: int


@dataclass(frozen=True)
class CompletenessThresholds:
    chains: int = 20
    stores: int = 700
    products: int = 250_000
    prices: int = 8_000_000


@dataclass(frozen=True)
class ImportResult:
    chains: int
    stores: int
    products: int
    prices: int
    duration_seconds: float
    skipped: bool = False


def _open(path: Path):
    return path.open("r", encoding="utf-8", newline="")


def _dict_reader(path: Path, headers: list[str]):
    file = _open(path)
    try:
        reader = csv.DictReader(file)
        if reader.fieldnames != headers:
            raise ValueError(f"Unexpected headers in {path}: {reader.fieldnames!r}; expected {headers!r}")
        return file, reader
    except Exception:
        file.close()
        raise


def _identifier(row, field: str, path: Path, line: int) -> str:
    value = row.get(field)
    if value is None or not value.strip():
        raise ValueError(f"Missing {field} in {path}:{line}")
    return value


def _row_shape(row, path: Path, line: int) -> None:
    if None in row or any(value is None for value in row.values()):
        raise ValueError(f"Malformed CSV row in {path}:{line}")


def _numeric(value: str | None, field: str, path: Path, line: int) -> None:
    if value in (None, ""):
        return
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {field} in {path}:{line}: {value!r}") from exc
    if not number.is_finite():
        raise ValueError(f"Non-finite {field} in {path}:{line}")


def validate_dataset(
    dataset_path: Path,
    minimums: CompletenessThresholds | None = None,
) -> DatasetValidation:
    minimums = minimums or CompletenessThresholds()
    if not dataset_path.is_dir():
        raise ValueError(f"Dataset directory does not exist: {dataset_path}")
    root_files = [entry.name for entry in dataset_path.iterdir() if not entry.is_dir()]
    if any(name != "archive-info.txt" for name in root_files):
        raise ValueError(f"Unexpected files at dataset root: {root_files!r}")
    chain_paths = sorted(entry for entry in dataset_path.iterdir() if entry.is_dir())
    if not chain_paths:
        raise ValueError("Dataset contains no chain directories")
    chains = []
    total_stores = total_products = total_prices = 0
    required = {"stores.csv", "products.csv", "prices.csv"}
    for chain_path in chain_paths:
        entries = list(chain_path.iterdir())
        if {entry.name for entry in entries} != required or any(not entry.is_file() for entry in entries):
            raise ValueError(f"Chain {chain_path.name!r} must contain exactly {sorted(required)!r}")
        stores: set[str] = set()
        file, reader = _dict_reader(chain_path / "stores.csv", STORE_HEADERS)
        with file:
            for line, row in enumerate(reader, 2):
                _row_shape(row, Path(file.name), line)
                value = _identifier(row, "store_id", Path(file.name), line)
                if value in stores:
                    raise ValueError(f"Duplicate store_id {value!r} in {file.name}")
                stores.add(value)
        products: set[str] = set()
        file, reader = _dict_reader(chain_path / "products.csv", PRODUCT_HEADERS)
        with file:
            for line, row in enumerate(reader, 2):
                _row_shape(row, Path(file.name), line)
                value = _identifier(row, "product_id", Path(file.name), line)
                if value in products:
                    raise ValueError(f"Duplicate product_id {value!r} in {file.name}")
                products.add(value)
        prices = 0
        file, reader = _dict_reader(chain_path / "prices.csv", PRICE_HEADERS)
        with file:
            for line, row in enumerate(reader, 2):
                _row_shape(row, Path(file.name), line)
                store_id = _identifier(row, "store_id", Path(file.name), line)
                product_id = _identifier(row, "product_id", Path(file.name), line)
                if store_id not in stores:
                    raise ValueError(f"Unknown store_id {store_id!r} in {file.name}:{line}")
                if product_id not in products:
                    raise ValueError(f"Unknown product_id {product_id!r} in {file.name}:{line}")
                for field in PRICE_HEADERS[2:]:
                    _numeric(row.get(field), field, Path(file.name), line)
                prices += 1
        if not stores or not products or not prices:
            raise ValueError(f"Chain {chain_path.name!r} contains an empty required dataset")
        chain = ChainDataset(chain_path.name, chain_path, len(stores), len(products), prices)
        chains.append(chain)
        total_stores += chain.stores
        total_products += chain.products
        total_prices += chain.prices
    validation = DatasetValidation(tuple(chains), total_stores, total_products, total_prices)
    actual = {
        "chains": len(validation.chains),
        "stores": validation.stores,
        "products": validation.products,
        "prices": validation.prices,
    }
    required_totals = {
        "chains": minimums.chains,
        "stores": minimums.stores,
        "products": minimums.products,
        "prices": minimums.prices,
    }
    LOG.info(
        "Incoming dataset totals: chains=%d stores=%d products=%d prices=%d",
        actual["chains"], actual["stores"], actual["products"], actual["prices"],
    )
    LOG.info(
        "Completeness minimums: chains=%d stores=%d products=%d prices=%d",
        required_totals["chains"], required_totals["stores"],
        required_totals["products"], required_totals["prices"],
    )
    failures = [
        f"{name}={actual[name]} (minimum {required})"
        for name, required in required_totals.items()
        if actual[name] < required
    ]
    if failures:
        raise ValueError(
            "Dataset completeness thresholds failed: " + "; ".join(failures)
        )
    return validation


class CsvTransformStream(io.TextIOBase):
    """Bounded-memory CSV stream that adds chain_id and import_date fields."""

    def __init__(self, path: Path, prefix: list[object], suffix: list[object] | None = None):
        self.source = _open(path)
        self.reader = csv.reader(self.source)
        next(self.reader)
        self.prefix, self.suffix = prefix, suffix or []
        self.buffer, self.finished = "", False

    def readable(self):
        return True

    def read(self, size=-1):
        chunks = [self.buffer]
        buffered = len(self.buffer)
        self.buffer = ""
        while not self.finished and (size < 0 or buffered < size):
            try:
                row = next(self.reader)
            except StopIteration:
                self.finished = True
                self.source.close()
                break
            output = io.StringIO()
            csv.writer(output, lineterminator="\n").writerow(self.prefix + row + self.suffix)
            chunk = output.getvalue()
            chunks.append(chunk)
            buffered += len(chunk)
        combined = "".join(chunks)
        result = combined if size < 0 else combined[:size]
        self.buffer = "" if size < 0 else combined[size:]
        return result

    def close(self):
        if not self.source.closed:
            self.source.close()
        super().close()


def _chain_id(cursor, name: str) -> int:
    cursor.execute("INSERT INTO chains (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (name,))
    cursor.execute("SELECT id FROM chains WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Could not resolve chain {name!r}")
    return row[0]


def _copy(cursor, sql: str, stream: CsvTransformStream):
    try:
        cursor.copy_expert(sql, stream, size=1024 * 1024)
    finally:
        stream.close()


def replace_snapshot(connection, validation: DatasetValidation, archive_date: date,
                     lock_timeout="30s", statement_timeout="6h") -> ImportResult:
    started = monotonic()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = %s", (lock_timeout,))
            cursor.execute("SET LOCAL statement_timeout = %s", (statement_timeout,))
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", (0x43494A454E45,))
            if not cursor.fetchone()[0]:
                raise RuntimeError("Another refresh holds the advisory lock")
            cursor.execute("SELECT import_date FROM prices LIMIT 1")
            row = cursor.fetchone()
            if row is not None:
                if row[0] is None:
                    raise RuntimeError("Current snapshot has a NULL import_date")
                if row[0] >= archive_date:
                    return ImportResult(0, 0, 0, 0, monotonic() - started, True)
            cursor.execute("TRUNCATE TABLE prices, products, stores")
            ids = {chain.name: _chain_id(cursor, chain.name) for chain in validation.chains}
            specifications = [
                ("stores", "chain_id, store_id, type, address, city, zipcode", "stores.csv", None),
                ("products", "chain_id, product_id, barcode, name, brand, category, unit, quantity", "products.csv", None),
                ("prices", "chain_id, store_id, product_id, price, unit_price, best_price_30, anchor_price, special_price, import_date", "prices.csv", archive_date.isoformat()),
            ]
            for table, columns, filename, suffix in specifications:
                for chain in validation.chains:
                    stream = CsvTransformStream(chain.path / filename, [ids[chain.name]], [] if suffix is None else [suffix])
                    _copy(cursor, f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT CSV, NULL '')", stream)
            cursor.execute("SELECT COUNT(*) FROM stores")
            stores = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM products")
            products = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*), MIN(import_date), MAX(import_date) FROM prices")
            prices, minimum, maximum = cursor.fetchone()
            actual = stores, products, prices
            expected = validation.stores, validation.products, validation.prices
            if actual != expected:
                raise RuntimeError(f"Post-import counts differ: database={actual}, expected={expected}")
            if minimum != archive_date or maximum != archive_date:
                raise RuntimeError(f"Post-import date check failed: {minimum}..{maximum}")
            cursor.execute("""SELECT EXISTS (SELECT 1 FROM prices pr WHERE
                NOT EXISTS (SELECT 1 FROM stores s WHERE s.chain_id=pr.chain_id AND s.store_id=pr.store_id)
                OR NOT EXISTS (SELECT 1 FROM products p WHERE p.chain_id=pr.chain_id AND p.product_id=pr.product_id)
                LIMIT 1)""")
            if cursor.fetchone()[0]:
                raise RuntimeError("Post-import validation found orphan prices")
    return ImportResult(len(validation.chains), validation.stores, validation.products,
                        validation.prices, monotonic() - started)
