import os
import pytest
import psycopg2
from db_client.db_client import get_connection, init_db
import db_client.db_client as db_mod

class DummyCursor:
    def __init__(self):
        self.queries = []
    def execute(self, query, params=None):
        self.queries.append((query, params))
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
def patch_psycopg_connect(monkeypatch):
    # Prevent loading .env
    monkeypatch.setattr(db_mod, 'load_dotenv', lambda: None)
    # Set env vars for get_connection
    monkeypatch.setenv('DB_NAME', 'testdb')
    monkeypatch.setenv('DB_USER', 'user')
    monkeypatch.setenv('DB_PASSWORD', 'pass')
    monkeypatch.setenv('DB_HOST', 'localhost')
    monkeypatch.setenv('DB_PORT', '5432')
    dummy_cursor = DummyCursor()
    dummy_conn = DummyConnection(dummy_cursor)
    monkeypatch.setattr(psycopg2, 'connect', lambda **kwargs: dummy_conn)
    return dummy_cursor, dummy_conn

def test_get_connection_returns_connection():
    conn = get_connection()
    assert conn is not None

def test_init_db_executes_create_table(patch_psycopg_connect):
    dummy_cursor, dummy_conn = patch_psycopg_connect
    init_db()
    assert any('CREATE TABLE IF NOT EXISTS emails' in q for q, _ in dummy_cursor.queries)
    assert dummy_conn.closed
