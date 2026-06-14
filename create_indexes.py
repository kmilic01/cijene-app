import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

cur.execute("CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_products_chain_product ON products(chain_id, product_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_chain_product ON prices(chain_id, product_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_store ON prices(chain_id, store_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_stores_chain_store ON stores(chain_id, store_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_stores_city ON stores(city);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_chains_name ON chains(name);")

conn.commit()
cur.close()
conn.close()

print("Indeksi su uspješno kreirani.")