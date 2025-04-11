import psycopg2
from dotenv import load_dotenv
import os
from db_client.db_client import init_db
from mail_clients.gmail_client import get_gmail_service
from mail_clients.email_client import fetch_and_store_emails

def main():
    load_dotenv()
    init_db()
    fetch_and_store_emails()

    

if __name__ == "__main__":
    main()
