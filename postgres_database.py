import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

connection = psycopg2.connect(
    os.getenv("DATABASE_URL")
)

print("Spojeno na PostgreSQL!")

connection.close()