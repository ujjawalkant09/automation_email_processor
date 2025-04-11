
from .gmail_client import get_gmail_service
from email.utils import parsedate_to_datetime
from process.email_processor import EmailRepository
from googleapiclient.errors import HttpError


def fetch_and_store_emails():
    """
    Fetches emails from Gmail and stores them in the DB.
    """
    service = get_gmail_service()
    try:
        response = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = response.get('messages', [])

        for msg in messages:
            msg_detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
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

            # Extract relevant headers
            for h in headers:
                name = h['name'].lower()
                if name == 'subject':
                    subject = h['value']
                elif name == 'from':
                    sender = h['value']
                elif name == 'date':
                    # Convert from RFC 2822 date string to datetime
                    date_received = parsedate_to_datetime(h['value'])

            is_read = 'UNREAD' not in label_ids

            email_record = {
                "gmail_id": gmail_id,
                "thread_id": thread_id,
                "sender": sender,
                "subject": subject,
                "snippet": snippet,
                "date_received": date_received,
                "is_read": is_read,
                "labels": label_ids,
            }
            EmailRepository.insert_email(email_record)

    except HttpError as error:
        print(f"An error occurred: {error}")
