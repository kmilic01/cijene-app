from fastapi import FastAPI, Query
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Cijene proizvoda",
    description="Završni rad - analiza cijena proizvoda",
    version="1.0.0"
)

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@app.get("/")
def root():
    return {"message": "Aplikacija radi!"}


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/products/{lanac}")
def products(lanac: str, limit: int = Query(20, ge=1, le=500)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.product_id, p.barcode, p.name, p.brand, p.category, p.unit, p.quantity
        FROM products p
        JOIN chains c ON p.chain_id = c.id
        WHERE c.name = %s
        ORDER BY p.name
        LIMIT %s
    """, (lanac, limit))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "product_id": row[0],
            "barcode": row[1],
            "name": row[2],
            "brand": row[3],
            "category": row[4],
            "unit": row[5],
            "quantity": row[6]
        }
        for row in rows
    ]


@app.get("/stores/{lanac}")
def stores(lanac: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.store_id, s.type, s.address, s.city, s.zipcode
        FROM stores s
        JOIN chains c ON s.chain_id = c.id
        WHERE c.name = %s
        ORDER BY s.city, s.address
    """, (lanac,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "store_id": row[0],
            "type": row[1],
            "address": row[2],
            "city": row[3],
            "zipcode": row[4]
        }
        for row in rows
    ]


@app.get("/prices/{lanac}")
def prices(lanac: str, limit: int = Query(20, ge=1, le=500)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            p.store_id,
            p.product_id,
            p.price,
            p.unit_price,
            p.best_price_30,
            p.anchor_price,
            p.special_price,
            p.import_date
        FROM prices p
        JOIN chains c ON p.chain_id = c.id
        WHERE c.name = %s
        LIMIT %s
    """, (lanac, limit))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "store_id": row[0],
            "product_id": row[1],
            "price": float(row[2]) if row[2] is not None else None,
            "unit_price": float(row[3]) if row[3] is not None else None,
            "best_price_30": float(row[4]) if row[4] is not None else None,
            "anchor_price": float(row[5]) if row[5] is not None else None,
            "special_price": float(row[6]) if row[6] is not None else None,
            "import_date": str(row[7]) if row[7] is not None else None
        }
        for row in rows
    ]