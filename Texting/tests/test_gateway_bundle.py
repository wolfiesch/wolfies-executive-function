"""
Tests for the gateway "bundle" command.

These tests are unit-level and do not require access to macOS Messages.db.
We patch `get_interfaces()` to return a fake MessagesInterface + ContactsManager.
"""

import json
import sys
import os

import pytest

# Add Texting/ to path (match existing test pattern in this repo)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from gateway import imessage_client


class _FakeContact:
    """Minimal contact stand-in for bundle tests."""

    def __init__(self, name: str, phone: str):
        self.name = name
        self.phone = phone


class _FakeContactsManager:
    """Minimal ContactsManager stand-in for bundle tests."""

    def __init__(self, contacts: list[_FakeContact]):
        self._contacts = contacts

    def get_contact_by_name(self, name: str):
        for c in self._contacts:
            if c.name == name:
                return c
        return None


class _FakeMessagesInterface:
    """Minimal MessagesInterface stand-in for bundle tests."""

    def __init__(self):
        self.calls = []

    def get_unread_count(self) -> int:
        self.calls.append(("get_unread_count",))
        return 2

    def get_unread_messages(self, limit: int = 50):
        self.calls.append(("get_unread_messages", limit))
        return [
            {
                "text": "hello from +1",
                "date": "2026-01-01T00:00:00",
                "phone": "+111",
                "days_old": 0,
                "group_id": None,
                "group_name": None,
            },
            {
                "text": "hello from +2",
                "date": "2026-01-01T00:00:01",
                "phone": "+222",
                "days_old": 1,
                "group_id": None,
                "group_name": None,
            },
        ][:limit]

    def get_all_recent_conversations(self, limit: int = 10):
        self.calls.append(("get_all_recent_conversations", limit))
        return [
            {"date": "2026-01-01T00:00:02", "is_from_me": False, "phone": "+111", "text": "recent", "group_id": None}
        ][:limit]

    def search_messages(self, query: str, phone: str | None = None, limit: int = 50, since=None):
        self.calls.append(("search_messages", query, phone, limit, since))
        return [
            {
                "date": "2026-01-01T00:00:03",
                "is_from_me": False,
                "phone": phone or "+333",
                "text": f"match {query}",
                "match_snippet": f"...{query}...",
                "group_id": None,
            }
        ][:limit]

    def get_messages_by_phone(self, phone: str, limit: int = 20):
        self.calls.append(("get_messages_by_phone", phone, limit))
        return [
            {"date": "2026-01-01T00:00:04", "is_from_me": True, "text": "hi", "group_id": None}
        ][:limit]

def test_bundle_basic_json_compact(monkeypatch, capsys):
    """Bundle returns expected top-level keys and compact JSON when requested."""
    fake_mi = _FakeMessagesInterface()
    fake_cm = _FakeContactsManager([_FakeContact("John", "+15551234567")])
    monkeypatch.setattr(imessage_client, "get_interfaces", lambda: (fake_mi, fake_cm))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wolfies-imessage",
            "bundle",
            "--json",
            "--compact",
            "--query",
            "http",
            "--search-limit",
            "5",
        ],
    )

    code = imessage_client.main()
    assert code == 0

    stdout = capsys.readouterr().out.strip()
    assert "\n" not in stdout  # compact JSON
    payload = json.loads(stdout)

    assert "meta" in payload
    assert "unread" in payload
    assert "recent" in payload
    assert "search" in payload

    assert payload["unread"]["count"] == 2
    assert isinstance(payload["unread"]["messages"], list)


def test_bundle_contact_includes_contact_messages_and_scopes_search(monkeypatch, capsys):
    """When contact is provided, bundle can include contact_messages and scope search."""
    fake_mi = _FakeMessagesInterface()
    fake_cm = _FakeContactsManager([_FakeContact("John", "+15551234567")])
    monkeypatch.setattr(imessage_client, "get_interfaces", lambda: (fake_mi, fake_cm))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wolfies-imessage",
            "bundle",
            "--json",
            "--contact",
            "John",
            "--query",
            "meeting",
            "--search-scoped-to-contact",
            "--messages-limit",
            "10",
        ],
    )

    code = imessage_client.main()
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["meta"]["contact"]["name"] == "John"
    assert "contact_messages" in payload

    # Ensure search_messages was invoked with phone filter.
    search_calls = [c for c in fake_mi.calls if c[0] == "search_messages"]
    assert search_calls, "expected search_messages to be called"
    _, query, phone, limit, since = search_calls[-1]
    assert query == "meeting"
    assert phone == "+15551234567"


def test_bundle_fields_filter_applies_to_message_lists(monkeypatch, capsys):
    """--fields should reduce output keys across message-like lists."""
    fake_mi = _FakeMessagesInterface()
    fake_cm = _FakeContactsManager([_FakeContact("John", "+15551234567")])
    monkeypatch.setattr(imessage_client, "get_interfaces", lambda: (fake_mi, fake_cm))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wolfies-imessage",
            "bundle",
            "--json",
            "--fields",
            "date,text",
        ],
    )

    code = imessage_client.main()
    assert code == 0
    payload = json.loads(capsys.readouterr().out)

    unread_msgs = payload["unread"]["messages"]
    assert unread_msgs, "expected unread messages in payload"
    assert set(unread_msgs[0].keys()).issubset({"date", "text"})


def test_bundle_include_limits_work(monkeypatch, capsys):
    """--include should avoid running (and emitting) sections not requested."""
    fake_mi = _FakeMessagesInterface()
    fake_cm = _FakeContactsManager([_FakeContact("John", "+15551234567")])
    monkeypatch.setattr(imessage_client, "get_interfaces", lambda: (fake_mi, fake_cm))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wolfies-imessage",
            "bundle",
            "--json",
            "--include",
            "unread_count",
        ],
    )

    code = imessage_client.main()
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert "meta" in payload
    assert "unread" in payload
    assert "count" in payload["unread"]
    assert "messages" not in payload["unread"]
    assert "recent" not in payload
    assert "search" not in payload

    # Ensure we didn't call methods we didn't need.
    called = [c[0] for c in fake_mi.calls]
    assert "get_unread_count" in called
    assert "get_unread_messages" not in called
    assert "get_all_recent_conversations" not in called
    assert "search_messages" not in called


def test_bundle_minimal_preset_reduces_fields(monkeypatch, capsys):
    """--minimal should default to date/phone/is_from_me/text (plus match_snippet for searches)."""
    fake_mi = _FakeMessagesInterface()
    fake_cm = _FakeContactsManager([_FakeContact("John", "+15551234567")])
    monkeypatch.setattr(imessage_client, "get_interfaces", lambda: (fake_mi, fake_cm))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wolfies-imessage",
            "bundle",
            "--json",
            "--minimal",
            "--query",
            "http",
            "--search-limit",
            "1",
        ],
    )

    code = imessage_client.main()
    assert code == 0

    stdout = capsys.readouterr().out.strip()
    assert "\n" not in stdout  # minimal implies compact JSON

    payload = json.loads(stdout)
    unread = payload["unread"]["messages"]
    assert unread, "expected unread messages in payload"
    assert set(unread[0].keys()).issubset({"date", "phone", "is_from_me", "text"})

    search = payload["search"]["results"]
    assert search, "expected search results in payload"
    assert set(search[0].keys()).issubset({"date", "phone", "is_from_me", "text", "match_snippet"})
