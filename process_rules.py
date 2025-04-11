from dotenv import load_dotenv
import os
import json
from data_handler.email_processor import EmailRepository
from mail_clients.gmail_client import get_gmail_service
import datetime

from logger.logger import get_logger


logger = get_logger(__name__,"logs/process_rules")


def apply_rules():
    load_dotenv()
    rules_file = os.getenv("RULES_JSON_PATH")
    if not rules_file:
        logger.info("[apply_rules] No rules found. Exiting.")
        return

    with open(rules_file, 'r') as f:
        rules_data = json.load(f)

    top_level_predicate = rules_data.get("predicate", "All")
    rules = rules_data.get("rules", [])
    actions = rules_data.get("actions", [])

    emails = EmailRepository.get_emails_by_conditions(rules, top_level_predicate)
    logger.debug(f"[apply_rules] Found {len(emails)} matching emails")

    service = get_gmail_service()

    for email in emails:
        logger.debug(f"[apply_rules] Performing actions on email {email['gmail_id']}")
        for action in actions:
            perform_action(service, email, action)


def mark_as_read(service, message_id):
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def mark_as_unread(service, message_id):
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={"addLabelIds": ["UNREAD"]}
    ).execute()


def move_to_label(service, email, label_name):
    """
    Moves the message to the specified label (if the label exists).
    If it doesn't exist, create it.
    """
    message_id = email["gmail_id"]
    labels_response = service.users().labels().list(userId='me').execute()
    labels = labels_response.get('labels', [])
    label_id = None
    for lbl in labels:
        if lbl['name'].lower() == label_name.lower():
            label_id = lbl['id']
            break
    if not label_id:
        logger.debug(f"[move_to_label] Label '{label_name}' not found. Creating it.")
        new_label = service.users().labels().create(
            userId='me',
            body={'name': label_name}
        ).execute()
        label_id = new_label['id']

    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={"addLabelIds": [label_id]}
    ).execute()

    if "labels" not in email or email["labels"] is None:
        email["labels"] = []
    email["labels"].append(label_name) 
    EmailRepository.update_email(email)
    logger.info(f"[move_to_label] Email {message_id} moved to label '{label_name}'.")


def perform_action(service, email, action):
    gmail_id = email['gmail_id']
    action_lower = action.lower()

    # Mark as read
    if action_lower == "mark as read":
        if not email.get("is_read", False):
            logger.info(f"[perform_action] Marking email {gmail_id} as read.")
            mark_as_read(service, gmail_id)
            email["is_read"] = True
            EmailRepository.update_email(email)
        else:
            logger.debug(f"[perform_action Email {gmail_id} is already marked as read. Skipping...")

    # Mark as unread
    elif action_lower == "mark as unread":
        if email.get("is_read", False):
            logger.info(f"[perform_action] Marking email {gmail_id} as unread.")
            mark_as_unread(service, gmail_id)
            email["is_read"] = False
            EmailRepository.update_email(email)
        else:
            logger.debug(f"[perform_action] Email {gmail_id} is already unread. Skipping...")

    # Move to label
    elif action_lower.startswith("move message"):
        parts = action.split(":", 1)
        if len(parts) == 2:
            label_name = parts[1].strip()
            logger.info(f"[perform_action] Moving email {gmail_id} to label '{label_name}'.")
            move_to_label(service, email, label_name)


if __name__ == "__main__":
    apply_rules()