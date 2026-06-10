import sqlite3

connection = sqlite3.connect("cijene.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain_id INTEGER NOT NULL,
    store_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    price REAL,
    unit_price REAL,
    best_price_30 REAL,
    anchor_price REAL,
    special_price REAL,
    import_date TEXT,
    FOREIGN KEY (chain_id) REFERENCES chains(id)
)
""")

connection.commit()
connection.close()

print("Baza je uspješno kreirana!")