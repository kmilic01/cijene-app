import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

cur.execute("""
    SELECT c.name, COUNT(*)
    FROM products p
    JOIN chains c ON p.chain_id = c.id
    WHERE p.barcode = %s
    GROUP BY c.name
    ORDER BY c.name
""", ("3850354015864",))

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()