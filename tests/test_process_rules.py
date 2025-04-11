import os
import json
import pytest
import process_rules as pr_mod
import data_handler.email_processor as ep_mod


class FakeService:
    def __init__(self):
        self.labels_list = [{'id': '1', 'name': 'Inbox'}]
        self.modified    = []

    def users(self):
        return self

    def labels(self):
        return self

    def list(self, userId):
        return type('R', (), {
            'execute': lambda self=None, labels=self.labels_list: {'labels': labels}
        })()

    def create(self, userId, body):
        return type('R', (), {
            'execute': lambda self=None: {'id': 'newid', 'name': body['name']}
        })()

    def messages(self):
        return self

    def modify(self, userId, id, body):
        self.modified.append((id, body))
        return type('R', (), {'execute': lambda self=None: None})()

@pytest.fixture(autouse=True)
def patch_env_and_repo(tmp_path, monkeypatch):
    # Write a simple rules.json
    rules = {
        'predicate': 'All',
        'rules': [{'field': 'From', 'predicate': 'Contains', 'value': 'test'}],
        'actions': ['Mark as read']
    }
    rf = tmp_path / 'rules.json'
    rf.write_text(json.dumps(rules))
    monkeypatch.setenv('RULES_JSON_PATH', str(rf))

    # Stub out DB lookup
    monkeypatch.setattr(ep_mod.EmailRepository, 'get_emails_by_conditions',
                        lambda rules, pred: [{'gmail_id': '1', 'is_read': False, 'labels': []}])

def test_apply_rules_triggers_actions(monkeypatch):
    fake_service = FakeService()
    monkeypatch.setattr('process_rules.get_gmail_service', lambda: fake_service)

    calls = []
    monkeypatch.setattr('process_rules.perform_action',
                        lambda service, email, action: calls.append((email, action)))

    pr_mod.apply_rules()
    assert calls == [({'gmail_id': '1', 'is_read': False, 'labels': []}, 'Mark as read')]

def test_perform_action_mark_as_read(monkeypatch):
    
    fake_service = FakeService()
    email = {'gmail_id': '1', 'is_read': False, 'labels': []}
    monkeypatch.setattr(ep_mod.EmailRepository, 'update_email', lambda record: None)

    pr_mod.perform_action(fake_service, email, 'Mark as read')
    assert email['is_read']
    assert fake_service.modified[0][1] == {'removeLabelIds': ['UNREAD']}

def test_perform_action_move_to_label(monkeypatch):
    fake_service = FakeService()
    fake_service.labels_list = []  # force label creation
    monkeypatch.setattr(ep_mod.EmailRepository, 'update_email', lambda record: None)

    email = {'gmail_id': '1', 'is_read': True, 'labels': []}
    pr_mod.perform_action(fake_service, email, 'Move Message : Inbox')
    assert 'Inbox' in email['labels']
    assert any('addLabelIds' in body for _, body in fake_service.modified)
