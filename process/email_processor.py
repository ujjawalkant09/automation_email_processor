from db_client.db_client import get_connection

class EmailRepository:
    @staticmethod
    def insert_email(email_record):
        """
        email_record is a dict with keys:
        gmail_id, thread_id, sender, subject, messages, date_received, is_read, labels
        """
        query = """
            INSERT INTO emails (gmail_id, thread_id, sender, subject, messages, date_received, is_read, labels)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (gmail_id) DO NOTHING
            -- to avoid duplicates if we already fetched that ID
        """
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        query,
                        (
                            email_record["gmail_id"],
                            email_record.get("thread_id"),
                            email_record.get("sender"),
                            email_record.get("subject"),
                            email_record.get("messages"),
                            email_record.get("date_received"),
                            email_record.get("is_read"),
                            email_record.get("labels"),
                        )
                    )
        finally:
            conn.close()

    @staticmethod
    def get_all_emails():
        """Fetch all emails from the DB."""
        query = "SELECT * FROM emails;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                # Convert rows to a list of dict if needed
                columns = [desc[0] for desc in cur.description]
                results = []
                for row in rows:
                    results.append(dict(zip(columns, row)))
                return results
        finally:
            conn.close()





    
