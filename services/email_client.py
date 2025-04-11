
from .gmail_client import get_gmail_service
from email.utils import parsedate_to_datetime
from process.email_processor import EmailRepository
from googleapiclient.errors import HttpError


def fetch_and_store_emails():
    """
    Fetches emails from Gmail and stores them in the DB.
    """
    service = get_gmail_service()
    page_token = None

    try:
        while True:
            response = service.users().messages().list(
                userId='me',
                maxResults=5,  
                pageToken=page_token
            ).execute()

            messages = response.get('messages', [])
            if not messages:
                print("No Messages Found Breaking The Loops")
                break  

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

                EmailRepository.insert_email(email_record)

            page_token = response.get('nextPageToken')
            if not page_token:
                print("No page_token Found Breaking the loops")
                break

    except HttpError as error:
        print(f"An error occurred: {error}")
