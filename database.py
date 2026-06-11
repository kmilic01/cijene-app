import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

print("HOST:", os.getenv("DB_HOST"))
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

connection = psycopg2.connect(
    os.getenv("DATABASE_URL")
)

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chains (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stores (
    id SERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL,
    store_id TEXT NOT NULL,
    type TEXT,
    address TEXT,
    city TEXT,
    zipcode TEXT,
    FOREIGN KEY (chain_id) REFERENCES chains(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    barcode TEXT,
    name TEXT,
    brand TEXT,
    category TEXT,
    unit TEXT,
    quantity TEXT,
    FOREIGN KEY (chain_id) REFERENCES chains(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL,
    store_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    price NUMERIC,
    unit_price NUMERIC,
    best_price_30 NUMERIC,
    anchor_price NUMERIC,
    special_price NUMERIC,
    import_date DATE,
    FOREIGN KEY (chain_id) REFERENCES chains(id)
)
""")

connection.commit()
cursor.close()
connection.close()

print("PostgreSQL tablice su uspješno kreirane!")