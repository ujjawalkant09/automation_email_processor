
from .gmail_client import get_gmail_service
from email.utils import parsedate_to_datetime
from data_handler.email_processor import EmailRepository
from googleapiclient.errors import HttpError
from logger.logger import get_logger

logger = get_logger(__name__,"logs/email_client")

def fetch_and_store_emails():
    """
    Fetches emails from Gmail and stores/updates them in the DB.
    """
    logger.info("Starting fetch_and_store_emails function.")

    service = get_gmail_service()
    if not service:
        logger.error("Gmail service was not created successfully.")
        return

    page_token = None
    processed_count = 0
    updated_count = 0
    new_count = 0

    try:
        while True:
            response = service.users().messages().list(
                userId='me',
                maxResults=5,  
                pageToken=page_token
            ).execute()
            
            messages = response.get('messages', [])

            if not messages:
                logger.info("No messages found. Breaking out of the loop.")
                break

            for msg in messages:
                msg_id = msg['id']
                logger.debug("Processing message with id=%s", msg_id)
                
                msg_detail = service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='metadata'
                ).execute()

                gmail_id = msg_detail['id']
                thread_id = msg_detail.get('threadId')
                headers = msg_detail.get('payload', {}).get('headers', [])
                snippet = msg_detail.get('snippet', '')
                label_ids = msg_detail.get('labelIds', [])

                subject = None
                sender = None
                date_received = None

                for h in headers:
                    name = h['name'].lower()
                    if name == 'subject':
                        subject = h['value']
                    elif name == 'from':
                        sender = h['value']
                    elif name == 'date':
                        date_received = parsedate_to_datetime(h['value'])

                is_read = 'UNREAD' not in label_ids

                email_record = {
                    "gmail_id": gmail_id,
                    "thread_id": thread_id,
                    "sender": sender,
                    "subject": subject,
                    "messages": snippet,
                    "date_received": date_received,
                    "is_read": is_read,
                    "labels": label_ids,
                }

                result = EmailRepository.insert_or_update_email(email_record)
                processed_count += 1
                if result == "created":
                    new_count += 1
                elif result == 'updated':
                    updated_count += 1

            page_token = response.get('nextPageToken')
            if not page_token:
                logger.info("No nextPageToken found. Breaking out of the loop.")
                break

        logger.info(
            f"Email sync completed. Processed: {processed_count}, "
            f"New: {new_count}, Updated: {updated_count}"
        )

    except HttpError as error:
        logger.error("An error occurred: %s", error)
