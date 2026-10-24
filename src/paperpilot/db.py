import os 
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_conn() -> psycopg.Connection:
    return psycopg.connect(os.environ.get("DATABASE_URL"))