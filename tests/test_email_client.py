import pytest
import data_handler.email_processor as ep_mod
from mail_clients.email_client import fetch_and_store_emails

class FakeService:
    def __init__(self, messages_list, details_list):
        self._messages_list = messages_list
        self._details_list = details_list
        self._calls = 0

    def users(self):
        return self

    def messages(self):
        return self

    def list(self, userId, maxResults, pageToken):
        if self._calls == 0:
            self._calls += 1
            return type('R', (), {
                'execute': lambda self=None, msgs=self._messages_list: {
                    'messages': msgs, 'nextPageToken': None
                }
            })()
        return type('R', (), {'execute': lambda self=None: {'messages': []}})()

    def get(self, userId, id, format):
        detail = next(d for d in self._details_list if d['id'] == id)
        return type('R', (), {'execute': lambda self=None, detail=detail: detail})()

def test_fetch_and_store_emails(monkeypatch):
    msg_id = '1'
    messages_list = [{'id': msg_id}]
    detail = {
        'id': msg_id,
        'threadId': 't1',
        'payload': {'headers': [
            {'name': 'Subject', 'value': 'sub'},
            {'name': 'From',    'value': 'sender'},
            {'name': 'Date',    'value': 'Wed, 01 Jan 2020 00:00:00 +0000'}
        ]},
        'snippet': 'snippet',
        'labelIds': []
    }
    fake_service = FakeService(messages_list, [detail])
    monkeypatch.setattr('mail_clients.email_client.get_gmail_service',
                        lambda: fake_service)

    calls = []
    monkeypatch.setattr(ep_mod.EmailRepository, 'insert_or_update_email',
                        lambda record: calls.append(record) or 'created')

    fetch_and_store_emails()

    assert len(calls) == 1
    record = calls[0]
    assert record['gmail_id'] == msg_id
    assert record['subject']  == 'sub'
    assert record['sender']   == 'sender'
    assert record['messages'] == 'snippet'
