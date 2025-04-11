from dotenv import load_dotenv
import os
import json
from process.email_processor import EmailRepository
from services.gmail_client import get_gmail_service
import datetime

from logger.logger import get_logger


logger = get_logger(__name__,"logs/process_rules")


def apply_rules():
    load_dotenv()
    rules_file = os.getenv("RULES_JSON_PATH")
    if not rules_file:
        logger.info("No rules found. Exiting.")
        return

    logger.debug(f"Rules file path: {rules_file}")

    with open(rules_file, 'r') as f:
        rules_data = json.load(f)
    logger.debug(f"Loaded rules data: {rules_data}")

    emails = EmailRepository.get_all_emails()
    logger.debug(f"Fetched {len(emails)} emails from repository.")

    top_level_predicate = rules_data.get("predicate", "All")
    conditions = rules_data.get("rules", [])
    actions = rules_data.get("actions", [])

    service = get_gmail_service()

    # Evaluate each email
    for email in emails:
        match = evaluate_email_against_conditions(email, conditions, top_level_predicate)
        if match:
            logger.debug(f"Email {email['gmail_id']} matched the conditions. Performing actions.")
            for action in actions:
                perform_action(service, email, action)
        else:
            logger.debug(f"Email {email['gmail_id']} did NOT match the conditions. Skipping.")


def evaluate_email_against_conditions(email, conditions, top_level_predicate):
    results = []
    for cond in conditions:
        field = cond.get("field")
        pred = cond.get("predicate")
        value = cond.get("value")
        res = evaluate_single_condition(email, field, pred, value)
        results.append(res)
        logger.debug(
            f"Condition check - Field: {field}, Predicate: {pred}, Value: {value}, "
            f"Email ID: {email['gmail_id']}, Result: {res}"
        )

    if top_level_predicate.lower() == "all":
        return all(results)
    else:
        return any(results)


def evaluate_single_condition(email, field, pred, value):
    # Determine the email field to test
    if field.lower() == 'from':
        target_value = email.get('sender', '')
    elif field.lower() == 'subject':
        target_value = email.get('subject', '')
    elif field.lower() == 'message':
        target_value = email.get('snippet', '')
    elif field.lower() in ('received date', 'received date/time'):
        target_value = email.get('date_received', None)
    else:
        target_value = ''

    # String-based
    if isinstance(target_value, str):
        val_lower = value.lower()
        tgt_lower = target_value.lower()
        if pred.lower() == 'contains':
            return (val_lower in tgt_lower)
        elif pred.lower() == 'does not contain':
            return (val_lower not in tgt_lower)
        elif pred.lower() == 'equals':
            return (val_lower == tgt_lower)
        elif pred.lower() == 'does not equal':
            return (val_lower != tgt_lower)

    # Date-based (simple example for days)
    if isinstance(target_value, datetime.datetime):
        now = datetime.datetime.now()
        match_days = re.findall(r"(\d+)\s*days?", value)
        if match_days:
            days_offset = int(match_days[0])
            diff = (now - target_value).days
            if pred.lower() == 'less than':
                return diff < days_offset
            elif pred.lower() == 'greater than':
                return diff > days_offset

    return False


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
        logger.debug(f"Label '{label_name}' not found. Creating it.")
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
    logger.info(f"Email {message_id} moved to label '{label_name}'.")


def perform_action(service, email, action):
    gmail_id = email['gmail_id']
    action_lower = action.lower()

    # Mark as read
    if action_lower == "mark as read":
        if not email.get("is_read", False):
            logger.info(f"Marking email {gmail_id} as read.")
            mark_as_read(service, gmail_id)
            email["is_read"] = True
            EmailRepository.update_email(email)
        else:
            logger.debug(f"Email {gmail_id} is already marked as read. Skipping...")

    # Mark as unread
    elif action_lower == "mark as unread":
        if email.get("is_read", False):
            logger.info(f"Marking email {gmail_id} as unread.")
            mark_as_unread(service, gmail_id)
            email["is_read"] = False
            EmailRepository.update_email(email)
        else:
            logger.debug(f"Email {gmail_id} is already unread. Skipping...")

    # Move to label
    elif action_lower.startswith("move message"):
        parts = action.split(":", 1)
        if len(parts) == 2:
            label_name = parts[1].strip()
            current_labels_in_db = email.get("labels", [])
            label_name_lower = label_name.lower()
            already_labeled = any(lbl.lower() == label_name_lower for lbl in current_labels_in_db)
            if already_labeled:
                logger.debug(
                    f"Skipping move. Email {gmail_id} already has the '{label_name}' label in DB."
                )
            else:
                logger.info(f"Moving email {gmail_id} to label '{label_name}'.")
                move_to_label(service, email, label_name)


if __name__ == "__main__":
    apply_rules()