import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add src to path if needed (matching existing test pattern)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.messages_interface import MessagesInterface

@pytest.fixture
def interface():
    interface = MessagesInterface(messages_db_path="/tmp/fake_chat.db")
    # Mock the Path object's exists method
    interface.messages_db_path = MagicMock(spec=Path)
    interface.messages_db_path.exists.return_value = True
    return interface

def test_detect_follow_up_needed_logic(interface):
    """Test that unanswered questions are correctly identified."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Cocoa epoch: 2001-01-01
    cocoa_epoch = datetime(2001, 1, 1)
    
    # Question from them 2 days ago, no reply
    two_days_ago = datetime.now() - timedelta(days=2)
    two_days_ago_cocoa = int((two_days_ago - cocoa_epoch).total_seconds() * 1_000_000_000)
    
    # (text, attributedBody, date_cocoa, is_from_me, phone, rowid)
    rows = [
        ("What time is the meeting?", None, two_days_ago_cocoa, 0, "+1234567890", 1),
    ]
    
    mock_cursor.fetchall.return_value = rows
    
    with patch('sqlite3.connect', return_value=mock_conn):
        follow_ups = interface.detect_follow_up_needed(days=7, min_stale_days=3)
        
        assert len(follow_ups["unanswered_questions"]) == 1
        assert follow_ups["unanswered_questions"][0]["phone"] == "+1234567890"
        assert "What time is the meeting?" in follow_ups["unanswered_questions"][0]["text"]

def test_detect_follow_up_needed_with_reply(interface):
    """Test that answered questions are NOT identified as needing follow-up."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    cocoa_epoch = datetime(2001, 1, 1)
    
    now = datetime.now()
    two_days_ago = now - timedelta(days=2)
    one_day_ago = now - timedelta(days=1)
    
    # Rows are ordered by date DESC in the function
    rows = [
        ("Sure thing", None, int((one_day_ago - cocoa_epoch).total_seconds() * 1_000_000_000), 1, "+1234567890", 2),
        ("Can you help?", None, int((two_days_ago - cocoa_epoch).total_seconds() * 1_000_000_000), 0, "+1234567890", 1),
    ]
    
    mock_cursor.fetchall.return_value = rows
    
    with patch('sqlite3.connect', return_value=mock_conn):
        follow_ups = interface.detect_follow_up_needed()
        # Question was answered, so unanswered_questions should be empty
        assert len(follow_ups["unanswered_questions"]) == 0

def test_detect_stale_conversations(interface):
    """Test detection of stale conversations (no reply after some time)."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    cocoa_epoch = datetime(2001, 1, 1)
    
    # Conversation stale for 5 days
    five_days_ago = datetime.now() - timedelta(days=5)
    
    rows = [
        ("Hello?", None, int((five_days_ago - cocoa_epoch).total_seconds() * 1_000_000_000), 0, "+9999999999", 1),
    ]
    
    mock_cursor.fetchall.return_value = rows
    
    with patch('sqlite3.connect', return_value=mock_conn):
        follow_ups = interface.detect_follow_up_needed(min_stale_days=3)
        assert len(follow_ups["stale_conversations"]) == 1
        assert follow_ups["stale_conversations"][0]["phone"] == "+9999999999"

def test_detect_promises_and_waiting(interface):
    """Test detection of promises made and things waiting on them."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    cocoa_epoch = datetime(2001, 1, 1)
    
    one_hour_ago = datetime.now() - timedelta(hours=1)
    one_hour_ago_cocoa = int((one_hour_ago - cocoa_epoch).total_seconds() * 1_000_000_000)
    
    rows = [
        ("I'll send it later", None, one_hour_ago_cocoa, 1, "+1112223333", 1),
        ("Let me know when you're ready", None, one_hour_ago_cocoa, 1, "+4445556666", 2),
    ]
    
    mock_cursor.fetchall.return_value = rows
    
    with patch('sqlite3.connect', return_value=mock_conn):
        follow_ups = interface.detect_follow_up_needed()
        # "I'll send it later" is a promise.
        # "Let me know when you're ready" matches "let me know" (waiting), 
        # but the negative lookahead (?! know) prevents it from matching "let me" (promise).
        assert len(follow_ups["pending_promises"]) == 1
        assert follow_ups["pending_promises"][0]["phone"] == "+1112223333"
        
        assert len(follow_ups["waiting_on_them"]) == 1
        assert follow_ups["waiting_on_them"][0]["phone"] == "+4445556666"

def test_detect_time_sensitive(interface):
    """Test detection of time-sensitive messages."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    cocoa_epoch = datetime(2001, 1, 1)
    
    now_cocoa = int((datetime.now() - cocoa_epoch).total_seconds() * 1_000_000_000)
    
    rows = [
        ("See you tomorrow", None, now_cocoa, 0, "+7778889999", 1),
    ]
    
    mock_cursor.fetchall.return_value = rows
    
    with patch('sqlite3.connect', return_value=mock_conn):
        follow_ups = interface.detect_follow_up_needed()
        assert len(follow_ups["time_sensitive"]) == 1
        assert follow_ups["time_sensitive"][0]["phone"] == "+7778889999"
        assert "tomorrow" in follow_ups["time_sensitive"][0]["text"]


def test_get_unread_count(interface):
    """Test unread count query returns expected integer."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = (7,)

    with patch('sqlite3.connect', return_value=mock_conn):
        count = interface.get_unread_count()
        assert count == 7
