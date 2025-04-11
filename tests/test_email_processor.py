import pytest
from data_handler.email_processor import EmailRepository
import data_handler.email_processor as ep_mod

class DummyCursor:
    def __init__(self, rows=None, description=None):
        self._rows = rows or []
        self._description = description or []
        self.queries = []
    def execute(self, query, params=None):
        self.queries.append((query, params))
    def fetchone(self):
        return self._rows[0] if self._rows else None
    def fetchall(self):
        return self._rows
    @property
    def description(self):
        return self._description
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass

class DummyConnection:
    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.closed = False
    def cursor(self):
        return self.cursor_obj
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
    def close(self):
        self.closed = True

@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    
    # Default get_connection returns an empty dummy
    monkeypatch.setattr(ep_mod, 'get_connection', lambda: DummyConnection(DummyCursor()))

def test_has_email_changed_same():
    existing = {
        'thread_id': 't', 'sender': 's', 'subject': 'sub',
        'messages': 'm', 'date_received': 1, 'is_read': True,
        'labels': ['a']
    }
    new = existing.copy()
    assert not EmailRepository._has_email_changed(existing, new)

def test_has_email_changed_diff():
    existing = {
        'thread_id': 't', 'sender': 's', 'subject': 'sub',
        'messages': 'm', 'date_received': 1, 'is_read': True,
        'labels': ['a']
    }
    new = existing.copy()
    new['subject'] = 'different'
    assert EmailRepository._has_email_changed(existing, new)

def test_insert_or_update_email_created(monkeypatch):
    # No existing record
    monkeypatch.setattr(EmailRepository, 'get_email_by_gmail_id', lambda x: None)
    # Simulate INSERT returning is_insert = True
    dummy_cursor = DummyCursor(rows=[(True,)])
    dummy_conn = DummyConnection(dummy_cursor)
    monkeypatch.setattr(ep_mod, 'get_connection', lambda: dummy_conn)

    record = {
        'gmail_id': 'id', 'thread_id': None, 'sender': None,
        'subject': None, 'messages': None,
        'date_received': None, 'is_read': None, 'labels': None
    }
    assert EmailRepository.insert_or_update_email(record) == 'created'

def test_insert_or_update_email_updated(monkeypatch):
    # Existing record that has changed
    monkeypatch.setattr(EmailRepository, 'get_email_by_gmail_id',
                        lambda x: {'gmail_id': 'id', 'thread_id': 'a', 'sender': 's',
                                   'subject': 'sub', 'messages': 'm',
                                   'date_received': 1, 'is_read': True, 'labels': ['a']})
    monkeypatch.setattr(EmailRepository, '_has_email_changed',
                        staticmethod(lambda a, b: True))
    dummy_cursor = DummyCursor(rows=[(False,)])
    dummy_conn = DummyConnection(dummy_cursor)
    monkeypatch.setattr(ep_mod, 'get_connection', lambda: dummy_conn)

    record = {
        'gmail_id': 'id', 'thread_id': 'b', 'sender': 's',
        'subject': 'sub', 'messages': 'm',
        'date_received': 1, 'is_read': True, 'labels': ['a']
    }
    assert EmailRepository.insert_or_update_email(record) == 'updated'

def test_insert_or_update_email_unchanged(monkeypatch):
    existing = {
        'gmail_id': 'id', 'thread_id': 'a', 'sender': 's',
        'subject': 'sub', 'messages': 'm',
        'date_received': 1, 'is_read': True, 'labels': ['a']
    }
    monkeypatch.setattr(EmailRepository, 'get_email_by_gmail_id', lambda x: existing)
    monkeypatch.setattr(EmailRepository, '_has_email_changed',
                        staticmethod(lambda a, b: False))

    record = existing.copy()
    assert EmailRepository.insert_or_update_email(record) == 'unchanged'

def test_get_email_by_gmail_id_found(monkeypatch):
    rows = [('id','t','s','sub','m','2021-01-01', True, ['a'])]
    desc = [('gmail_id',),('thread_id',),('sender',),('subject',),
            ('messages',),('date_received',),('is_read',),('labels',)]
    dummy_cursor = DummyCursor(rows=rows, description=desc)
    dummy_conn = DummyConnection(dummy_cursor)
    monkeypatch.setattr(ep_mod, 'get_connection', lambda: dummy_conn)

    result = EmailRepository.get_email_by_gmail_id('id')
    assert result['gmail_id'] == 'id'

def test_get_email_by_gmail_id_none(monkeypatch):
    dummy_cursor = DummyCursor(rows=[], description=[('gmail_id',)])
    dummy_conn = DummyConnection(dummy_cursor)
    monkeypatch.setattr(ep_mod, 'get_connection', lambda: dummy_conn)

    assert EmailRepository.get_email_by_gmail_id('id') is None

def test_get_all_emails(monkeypatch):
    rows = [
        ('id1','t','s','sub','m','2021-01-01', True, ['a']),
        ('id2','t2','s2','sub2','m2','2021-01-02', False, ['b'])
    ]
    desc = [('gmail_id',),('thread_id',),('sender',),('subject',),
            ('messages',),('date_received',),('is_read',),('labels',)]
    dummy_cursor = DummyCursor(rows=rows, description=desc)
    dummy_conn = DummyConnection(dummy_cursor)
    monkeypatch.setattr(ep_mod, 'get_connection', lambda: dummy_conn)

    result = EmailRepository.get_all_emails()
    assert isinstance(result, list) and len(result) == 2
    assert result[0]['gmail_id'] == 'id1'

def test_update_email(monkeypatch):
    dummy_cursor = DummyCursor()
    dummy_conn = DummyConnection(dummy_cursor)
    monkeypatch.setattr(ep_mod, 'get_connection', lambda: dummy_conn)

    # Should not raise
    EmailRepository.update_email({
        'gmail_id': 'id',
        'is_read': False,
        'labels': ['a']
    })
    assert dummy_conn.closed

def test_get_emails_by_conditions_contains(monkeypatch):
    rules = [{'field': 'From', 'predicate': 'Contains', 'value': 'test'}]
    desc = [('gmail_id',),('sender',)]
    rows = [('id1','sender1')]
    dummy_cursor = DummyCursor(rows=rows, description=desc)
    dummy_conn = DummyConnection(dummy_cursor)
    monkeypatch.setattr(ep_mod, 'get_connection', lambda: dummy_conn)

    result = EmailRepository.get_emails_by_conditions(rules, 'All')
    assert result[0]['gmail_id'] == 'id1'
