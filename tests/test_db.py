"""
Tests for utils/db.py - database operations
"""
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Use temp database for testing
_temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_PATH"] = _temp_db.name
os.environ["DATA_DIR"] = str(Path(_temp_db.name).parent)

# Re-import after setting env vars (force config reload)
import importlib
import config
importlib.reload(config)

from utils.db import (
    init_database, insert_issues, get_all_issues,
    get_issues_count, safe_replace_issues, get_statistics,
    search_issues, log_sync, get_last_sync
)


SAMPLE_ISSUES = [
    {
        "id": 1, "date": "01/23/2026", "channel": "rocm",
        "original_source": "", "category": "ROCm Issue",
        "issue": "Test issue 1", "owner": "Alice",
        "reply_approach": "", "progress": "Done",
        "result": "Resolved", "problem_category": "Setup/Drivers",
    },
    {
        "id": 2, "date": "01/24/2026", "channel": "pytorch",
        "original_source": "", "category": "PyTorch Issue",
        "issue": "Test issue 2", "owner": "Bob",
        "reply_approach": "", "progress": "In Progress",
        "result": "", "problem_category": "Library/Build",
    },
    {
        "id": 3, "date": "01/25/2026", "channel": "rocm",
        "original_source": "", "category": "Driver Issue",
        "issue": "Test issue 3", "owner": "Alice",
        "reply_approach": "", "progress": "Pending",
        "result": "", "problem_category": "Setup/Drivers",
    },
]


def test_init_database():
    """Test database initialization"""
    init_database()
    assert get_issues_count() == 0
    print("✅ test_init_database passed")


def test_insert_and_query():
    """Test insert and query operations"""
    count = insert_issues(SAMPLE_ISSUES)
    assert count == 3
    assert get_issues_count() == 3
    
    all_issues = get_all_issues()
    assert len(all_issues) == 3
    
    print("✅ test_insert_and_query passed")


def test_safe_replace():
    """Test safe replace (atomic transaction)"""
    new_issues = SAMPLE_ISSUES[:2]  # Only 2 records
    count = safe_replace_issues(new_issues)
    assert count == 2
    assert get_issues_count() == 2
    
    print("✅ test_safe_replace passed")


def test_search():
    """Test keyword search"""
    # Re-insert full data
    safe_replace_issues(SAMPLE_ISSUES)
    
    results = search_issues("ROCm")
    assert len(results) >= 1
    
    results = search_issues("nonexistent_keyword_xyz")
    assert len(results) == 0
    
    print("✅ test_search passed")


def test_statistics():
    """Test statistics computation"""
    safe_replace_issues(SAMPLE_ISSUES)
    
    stats = get_statistics()
    assert stats["total"] == 3
    assert "by_progress" in stats
    assert "by_problem_category" in stats
    
    print("✅ test_statistics passed")


def test_sync_log():
    """Test sync logging"""
    log_sync(3, "success", "Test sync")
    last = get_last_sync()
    assert last is not None
    assert last["rows_synced"] == 3
    assert last["status"] == "success"
    
    print("✅ test_sync_log passed")


def cleanup():
    """Remove temp database"""
    try:
        os.unlink(_temp_db.name)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        test_init_database()
        test_insert_and_query()
        test_safe_replace()
        test_search()
        test_statistics()
        test_sync_log()
        print("\n✅ All DB tests passed")
    finally:
        cleanup()
