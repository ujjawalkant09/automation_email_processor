import traceback
from db_client.db_client import get_connection
from logger.logger import get_logger
import re

logger = get_logger(__name__,"logs/email_processor")

class EmailRepository:
    @staticmethod
    def _has_email_changed(existing_email, new_email):
        fields_to_compare = [
            'thread_id', 'sender', 'subject', 'messages',
            'date_received', 'is_read', 'labels'
        ]
        
        for field in fields_to_compare:
            if existing_email.get(field) != new_email.get(field):
                return True
        return False

    @staticmethod
    def insert_or_update_email(email_record):
        """
        Insert new email or update existing one if data has changed.
        Returns:
            'created' - if new record was inserted
            'updated' - if existing record was updated
            'unchanged' - if existing record had no changes
        """

        existing_email = EmailRepository.get_email_by_gmail_id(email_record["gmail_id"])
        
        if existing_email:
            if not EmailRepository._has_email_changed(existing_email, email_record):
                logger.debug("[EmailRepository] No changes detected for email gmail_id=%s", email_record["gmail_id"])
                return 'unchanged'
        
        query = """
            INSERT INTO emails (gmail_id, thread_id, sender, subject, messages, 
                            date_received, is_read, labels)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (gmail_id) 
            DO UPDATE SET 
                thread_id = EXCLUDED.thread_id,
                sender = EXCLUDED.sender,
                subject = EXCLUDED.subject,
                messages = EXCLUDED.messages,
                date_received = EXCLUDED.date_received,
                is_read = EXCLUDED.is_read,
                labels = EXCLUDED.labels
            RETURNING (xmax = 0) AS is_insert
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
                    result = cur.fetchone()
                    return 'created' if result[0] else 'updated'
        except Exception as e:
            logger.error("[EmailRepository] Error upserting email: %s", e)
            logger.debug(traceback.format_exc())
            return 'error'
        finally:
            conn.close()

    @staticmethod
    def get_email_by_gmail_id(gmail_id):
        query = "SELECT * FROM emails WHERE gmail_id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (gmail_id,))
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error("[EmailRepository] Error fetching email by gmail_id: %s", e)
            logger.debug(traceback.format_exc())
            return None
        finally:
            conn.close()

    @staticmethod
    def get_all_emails():
        query = "SELECT * FROM emails;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in rows]
                return results
        except Exception as e:
            logger.error("[EmailRepository] Error fetching all emails: %s", e)
            logger.debug(traceback.format_exc())
        finally:
            conn.close()

    @staticmethod
    def update_email(email_record):
        logger.debug(
            "[EmailRepository] Updating email with gmail_id=%s, is_read=%s, labels=%s", 
            email_record.get("gmail_id"), 
            email_record.get("is_read"), 
            email_record.get("labels")
        )
        query = """
            UPDATE emails
            SET is_read = %s,
                labels = %s
            WHERE gmail_id = %s
        """
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        query,
                        (
                            email_record["is_read"],
                            email_record["labels"],
                            email_record["gmail_id"],
                        )
                    )
        except Exception as e:
            logger.error("[EmailRepository] Error updating email: %s", e)
            logger.debug(traceback.format_exc())
        finally:
            conn.close()
    
    @staticmethod
    def get_emails_by_conditions(rules: list, predicate: str) -> list:
        where_clauses = []
        params = []
        for rule in rules:
            field = rule['field'].lower()
            operator = rule['predicate'].lower()
            value = rule['value']
            
            field_map = {
                'from': 'sender',
                'subject': 'subject',
                'message': 'messages',
                'received date': 'date_received',
                'received date/time': 'date_received'
            }
            
            db_column = field_map.get(field)
            if not db_column:
                continue  

            # Convert operator to SQL
            if operator in ['contains', 'does not contain']:
                clause = f"{db_column} {'NOT ' if 'not' in operator else ''}ILIKE %s"
                val = f"%{value}%"
            elif operator in ['equals', 'does not equal']:
                clause = f"{db_column} {'!' if 'not' in operator else ''}= %s"
                val = value
            elif operator in ['less than', 'greater than'] and field in ['received date', 'received date/time']:
                days = re.findall(r"(\d+)\s*days?", value)
                if not days:
                    continue
                days = int(days[0])
                clause = f"(NOW() - date_received) {'<' if 'less' in operator else '>'} INTERVAL %s"
                val = f"{days} DAYS"
            else:
                logger.info(f"[EmailRepository] Unhandled predicate in rules :: {operator}")
                continue
            
            where_clauses.append(clause)
            params.append(val)
        if not where_clauses:
            return []

        # Combine clauses with AND/OR
        join_operator = " AND " if predicate.lower() == "all" else " OR "
        where_sql = join_operator.join(where_clauses)

        query = f"SELECT * FROM emails WHERE {where_sql};"
 
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error("[EmailRepository] Error fetching filtered emails: %s", e)
            return []
        finally:
            conn.close()

