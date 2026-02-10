"""
Tests for utils/common.py - shared constants and helpers
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.common import normalize_progress, parse_date, PROGRESS_COLORS, PROGRESS_VALUES


def test_normalize_progress():
    """Test progress normalization covers all known variants"""
    # Standard values
    assert normalize_progress("Done") == "Done"
    assert normalize_progress("In Progress") == "In Progress"
    assert normalize_progress("Pending") == "Pending"
    assert normalize_progress("Blocked") == "Blocked"
    
    # Case variants
    assert normalize_progress("done") == "Done"
    assert normalize_progress("DONE") == "Done"
    assert normalize_progress("in progress") == "In Progress"
    assert normalize_progress("pending") == "Pending"
    assert normalize_progress("block") == "Blocked"
    
    # Edge cases
    assert normalize_progress(None) == "Unknown"
    assert normalize_progress("") == "Unknown"
    assert normalize_progress("random_value") == "Unknown"
    
    # Whitespace
    assert normalize_progress("  Done  ") == "Done"
    
    print("✅ test_normalize_progress passed")


def test_parse_date():
    """Test date parsing with multiple formats"""
    # US format (Google Sheets default)
    dt = parse_date("01/23/2026")
    assert dt is not None
    assert dt.month == 1
    assert dt.day == 23
    assert dt.year == 2026
    
    # ISO format
    dt = parse_date("2026-01-23")
    assert dt is not None
    assert dt.year == 2026
    
    # Short year
    dt = parse_date("01/23/26")
    assert dt is not None
    
    # Edge cases
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("not a date") is None
    
    print("✅ test_parse_date passed")


def test_color_constants():
    """Verify all progress values have associated colors"""
    for val in PROGRESS_VALUES:
        assert val in PROGRESS_COLORS, f"Missing color for {val}"
    assert "Unknown" in PROGRESS_COLORS
    
    print("✅ test_color_constants passed")


if __name__ == "__main__":
    test_normalize_progress()
    test_parse_date()
    test_color_constants()
    print("\n✅ All common tests passed")
