import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

cur.execute("""
    SELECT
        c.name AS chain,
        p.barcode,
        p.product_id,
        p.name,
        p.brand,
        p.quantity,
        pr.price,
        pr.unit_price,
        pr.best_price_30,
        pr.special_price,
        s.city,
        s.address
    FROM products p
    JOIN chains c ON p.chain_id = c.id
    JOIN prices pr
        ON pr.chain_id = p.chain_id
        AND pr.product_id = p.product_id
    JOIN stores s
        ON s.chain_id = pr.chain_id
        AND s.store_id = pr.store_id
    WHERE LOWER(p.name) LIKE LOWER('%MILKA%OREO%')
    ORDER BY pr.price DESC
    LIMIT 50
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()