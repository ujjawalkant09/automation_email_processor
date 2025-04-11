import psycopg2
from dotenv import load_dotenv
import os
from db_client.db_client import init_db

def main():
    load_dotenv()
    init_db()
    print("Database initialized!")

    

if __name__ == "__main__":
    main()
