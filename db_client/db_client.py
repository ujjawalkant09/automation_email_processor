import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv



def get_connection():
    load_dotenv()
    # Read from environment
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")

    return psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )

def init_db():
    """Initialize the database (create table if not exists)."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS emails (
        id SERIAL PRIMARY KEY,
        gmail_id VARCHAR(255) NOT NULL UNIQUE,
        thread_id VARCHAR(255),
        sender VARCHAR(255),
        subject TEXT,
        snippet TEXT,
        date_received TIMESTAMP,
        is_read BOOLEAN,
        labels TEXT[]
    );
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(create_table_query)
    finally:
        conn.close()
