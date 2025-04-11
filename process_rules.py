from dotenv import load_dotenv
import os
import json
from process.email_processor import EmailRepository
from services.gmail_client import get_gmail_service
import datetime


def apply_rules():
    load_dotenv()
    rules_file = os.getenv("RULES_JSON_PATH")
    if not rules_file:
        print("No rules Found")
        return
    with open(rules_file, 'r') as f:
        rules_data = json.load(f)

    emails = EmailRepository.get_all_emails()
    top_level_predicate = rules_data.get("predicate", "All")
    conditions = rules_data.get("rules", [])
    actions = rules_data.get("actions", [])

    service = get_gmail_service()

    for email in emails:
        match = evaluate_email_against_conditions(email, conditions, top_level_predicate)
        if match:
            for action in actions:
                perform_action(service, email, action)


def evaluate_email_against_conditions(email, conditions, top_level_predicate):
    results = []
    for cond in conditions:
        field = cond.get("field")
        pred = cond.get("predicate")
        value = cond.get("value")
        results.append(evaluate_single_condition(email, field, pred, value))

    if top_level_predicate.lower() == "all":
        return all(results)
    return any(results)

    

def evaluate_single_condition(email, field, pred, value):
    if field.lower() == 'from':
        target_value = email['sender'] or ''
    elif field.lower() == 'subject':
        target_value = email['subject'] or ''
    elif field.lower() == 'message':
        target_value = email['snippet'] or ''
    elif field.lower() in ('received date', 'received date/time'):
        target_value = email['date_received']
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
    if isinstance(target_value, datetime):
        now = datetime.now()
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

def move_to_label(service, message_id, label_name):
    """
    Moves the message to the specified label (if the label exists).
    If it doesn't exist, you could create it or handle it differently.
    """
    # Find label ID by label name
    labels_response = service.users().labels().list(userId='me').execute()
    labels = labels_response.get('labels', [])
    label_id = None
    for lbl in labels:
        if lbl['name'].lower() == label_name.lower():
            label_id = lbl['id']
            break
    if not label_id:
        # Create label or do something else
        new_label = service.users().labels().create(
            userId='me',
            body={'name': label_name}
        ).execute()
        label_id = new_label['id']

    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={
            "addLabelIds": [label_id]
        }
    ).execute()


def perform_action(service, email, action):
    gmail_id = email['gmail_id']
    action_lower = action.lower()
    if action_lower == "mark as read":
        if not email["is_read"]:
            mark_as_read(service, gmail_id)
            email["is_read"] = True
            EmailRepository.update_email(email)
        else:
            print(f"Email {gmail_id} is already marked as read. Skipping...")

    elif action_lower == "mark as unread":
        if email["is_read"]:
            mark_as_unread(service, gmail_id)
            email["is_read"] = False
            EmailRepository.update_email(email)
        else:
             print(f"Email {gmail_id} is already unread. Skipping...")

    elif action_lower.startswith("move message"):
        parts = action.split(":", 1)
        if len(parts) == 2:
            label_name = parts[1].strip()
            move_to_label(service, gmail_id, label_name)



if __name__ == "__main__":
    apply_rules()