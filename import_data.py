import os
import csv
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

DATA_FOLDER = "podaci"
BATCH_SIZE = 250


def empty_to_none(value):
    return value if value != "" else None


connection = psycopg2.connect(
    os.getenv("DATABASE_URL")
)

cursor = connection.cursor()


def get_or_create_chain(chain_name):
    cursor.execute(
        """
        INSERT INTO chains (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING
        """,
        (chain_name,)
    )

    cursor.execute(
        "SELECT id FROM chains WHERE name = %s",
        (chain_name,)
    )

    return cursor.fetchone()[0]


def import_stores(chain_id, chain_path):
    stores_file = os.path.join(chain_path, "stores.csv")

    if not os.path.exists(stores_file):
        return

    rows = []

    with open(stores_file, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append((
                chain_id,
                row.get("store_id"),
                row.get("type"),
                row.get("address"),
                row.get("city"),
                row.get("zipcode")
            ))

    execute_batch(
        cursor,
        """
        INSERT INTO stores (chain_id, store_id, type, address, city, zipcode)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        rows,
        page_size=BATCH_SIZE
    )


def import_products(chain_id, chain_path):
    products_file = os.path.join(chain_path, "products.csv")

    if not os.path.exists(products_file):
        return

    rows = []

    with open(products_file, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append((
                chain_id,
                row.get("product_id"),
                row.get("barcode"),
                row.get("name"),
                row.get("brand"),
                row.get("category"),
                row.get("unit"),
                row.get("quantity")
            ))

    execute_batch(
        cursor,
        """
        INSERT INTO products (
            chain_id, product_id, barcode, name, brand, category, unit, quantity
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
        page_size=BATCH_SIZE
    )


def import_prices(chain_id, chain_path):
    prices_file = os.path.join(chain_path, "prices.csv")

    if not os.path.exists(prices_file):
        return

    rows = []
    total = 0

    with open(prices_file, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append((
                chain_id,
                row.get("store_id"),
                row.get("product_id"),
                empty_to_none(row.get("price")),
                empty_to_none(row.get("unit_price")),
                empty_to_none(row.get("best_price_30")),
                empty_to_none(row.get("anchor_price")),
                empty_to_none(row.get("special_price")),
                "2026-06-09"
            ))

            if len(rows) >= BATCH_SIZE:
                execute_batch(
                    cursor,
                    """
                    INSERT INTO prices (
                        chain_id, store_id, product_id, price, unit_price,
                        best_price_30, anchor_price, special_price, import_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                    page_size=BATCH_SIZE
                )
                connection.commit()
                total += len(rows)
                print(f"  prices uneseno: {total}")
                rows = []

    if rows:
        execute_batch(
            cursor,
            """
            INSERT INTO prices (
                chain_id, store_id, product_id, price, unit_price,
                best_price_30, anchor_price, special_price, import_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
            page_size=BATCH_SIZE
        )
        connection.commit()


for chain_name in os.listdir(DATA_FOLDER):
    chain_path = os.path.join(DATA_FOLDER, chain_name)

    if not os.path.isdir(chain_path):
        continue

    print(f"Uvozim lanac: {chain_name}")

    chain_id = get_or_create_chain(chain_name)

    import_stores(chain_id, chain_path)
    import_products(chain_id, chain_path)
    import_prices(chain_id, chain_path)

    connection.commit()
    print(f"Gotovo: {chain_name}")


cursor.close()
connection.close()

print("Svi podaci su uspješno uneseni u PostgreSQL!")