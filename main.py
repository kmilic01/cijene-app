from fastapi import FastAPI, Query
import os
import psycopg2
from dotenv import load_dotenv
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="Cijene proizvoda",
    description="Završni rad - analiza cijena proizvoda",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://cijene-app.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@app.get("/")
def root():
    return {"message": "Aplikacija radi!"}


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/search")
def search_products(
    query: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT
            barcode,
            name,
            brand,
            category,
            quantity,
            CASE
                WHEN LOWER(brand) LIKE LOWER(%s) THEN 1
                WHEN LOWER(name)  LIKE LOWER(%s) THEN 2
                WHEN LOWER(name)  LIKE LOWER(%s) THEN 3
                WHEN LOWER(brand) LIKE LOWER(%s) THEN 4
                ELSE 5
            END AS rank
        FROM products
        WHERE LOWER(name) LIKE LOWER(%s)
           OR LOWER(brand) LIKE LOWER(%s)
        ORDER BY rank, name
        LIMIT %s
    """, (
        f"{query}%",
        f"{query}%",
        f"%{query}%",
        f"%{query}%",
        f"%{query}%",
        f"%{query}%",
        limit,
    ))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "barcode": row[0],
            "name": row[1],
            "brand": row[2],
            "category": row[3],
            "quantity": row[4]
        }
        for row in rows
    ]


@app.get("/product/{barcode}/prices")
def product_prices(
    barcode: str,
    city: Optional[str] = None,
    chain: Optional[str] = None,
    sort: str = "asc"
):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        SELECT DISTINCT
            c.name,
            s.store_id,
            s.type,
            s.address,
            s.city,
            p.name,
            p.brand,
            p.category,
            pr.price,
            pr.unit_price,
            pr.best_price_30,
            pr.special_price,
            pr.import_date,
            p.quantity
        FROM products p
        JOIN chains c ON p.chain_id = c.id
        JOIN prices pr
            ON pr.chain_id = p.chain_id
            AND pr.product_id = p.product_id
        JOIN stores s
            ON s.chain_id = pr.chain_id
            AND s.store_id = pr.store_id
        WHERE p.barcode = %s
    """

    params = [barcode]

    if city:
        sql += " AND LOWER(s.city) = LOWER(%s)"
        params.append(city)

    if chain:
        sql += " AND LOWER(c.name) = LOWER(%s)"
        params.append(chain)

    if sort == "desc":
        sql += " ORDER BY pr.price DESC NULLS LAST"
    else:
        sql += " ORDER BY pr.price ASC NULLS LAST"

    cur.execute(sql, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "chain": row[0],
            #"store_id": row[1],
            #"store_type": row[2],
            "address": row[3],
            "city": row[4],
            "product_name": row[5],
            "quantity": row[13],
            #"brand": row[6],
            #"category": row[7],
            "price": float(row[8]) if row[8] is not None else None,
            "unit_price": float(row[9]) if row[9] is not None else None,
            "best_price_30": float(row[10]) if row[10] is not None else None,
            "special_price": float(row[11]) if row[11] is not None else None,
            #"import_date": str(row[12]) if row[12] is not None else None
        }
        for row in rows
    ]


@app.get("/cheapest/{barcode}")
def cheapest_product(
    barcode: str,
    city: Optional[str] = None
):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        SELECT
            c.name,
            s.city,
            s.address,
            pr.price,
            p.name
        FROM products p
        JOIN chains c
            ON p.chain_id = c.id
        JOIN prices pr
            ON pr.chain_id = p.chain_id
            AND pr.product_id = p.product_id
        JOIN stores s
            ON s.chain_id = pr.chain_id
            AND s.store_id = pr.store_id
        WHERE p.barcode = %s
            AND pr.price IS NOT NULL
    """

    params = [barcode]

    if city:
        sql += " AND LOWER(s.city) = LOWER(%s)"
        params.append(city)

    sql += """
        ORDER BY pr.price ASC
        LIMIT 1
    """

    cur.execute(sql, params)

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return {"message": "Proizvod nije pronađen"}

    return {
        "product_name": row[4],
        "chain": row[0],
        "city": row[1],
        "address": row[2],
        "price": float(row[3])
    }


@app.get("/cities")
def cities():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT city
        FROM stores
        WHERE city IS NOT NULL
        ORDER BY city
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [row[0] for row in rows]


@app.get("/chains")
def chains():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM chains
        ORDER BY name
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [row[0] for row in rows]


'''@app.get("/categories")
def categories():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
        ORDER BY category
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [row[0] for row in rows]
'''

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