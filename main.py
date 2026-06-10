from fastapi import FastAPI, Query
import csv

app = FastAPI(
    title="Cijene proizvoda",
    description="Završni rad - analiza cijena proizvoda",
    version="1.0.0"
)


@app.get("/")
def root():
    return {"message": "Aplikacija radi!"}


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/products/{lanac}")
def products(lanac: str, limit: int = Query(20, ge=1, le=500)):
    proizvodi = []

    with open(f"podaci/{lanac}/products.csv", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            proizvodi.append(row)

            if len(proizvodi) >= limit:
                break

    return proizvodi


@app.get("/stores/{lanac}")
def stores(lanac: str):
    trgovine = []

    with open(f"podaci/{lanac}/stores.csv", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            trgovine.append(row)

    return trgovine


@app.get("/prices/{lanac}")
def prices(lanac: str, limit: int = Query(20, ge=1, le=500)):
    cijene = []

    with open(f"podaci/{lanac}/prices.csv", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            cijene.append(row)

            if len(cijene) >= limit:
                break

    return cijene