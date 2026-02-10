"""
Tests for config.py - configuration and environment variables
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_config_loads():
    """Test config module loads without error"""
    from config import (
        PROJECT_ROOT, DATA_DIR, LOGS_DIR, DATABASE_PATH,
        CREDENTIALS_PATH, SPREADSHEET_ID, SHEET_NAME, SCOPES,
        COLUMN_MAPPING, CORE_FIELDS, ALL_FIELDS, DISPLAY_NAMES
    )
    
    assert PROJECT_ROOT.exists()
    assert isinstance(SPREADSHEET_ID, str) and len(SPREADSHEET_ID) > 0
    assert isinstance(SHEET_NAME, str) and len(SHEET_NAME) > 0
    assert len(SCOPES) > 0
    assert len(COLUMN_MAPPING) > 0
    assert "id" in ALL_FIELDS
    assert "progress" in ALL_FIELDS
    assert "problem_category" in ALL_FIELDS
    
    print("✅ test_config_loads passed")


def test_env_override():
    """Test environment variable overrides"""
    os.environ["SPREADSHEET_ID"] = "test_id_123"
    
    # Force reimport
    import importlib
    import config
    importlib.reload(config)
    
    assert config.SPREADSHEET_ID == "test_id_123"
    
    # Cleanup
    del os.environ["SPREADSHEET_ID"]
    importlib.reload(config)
    
    print("✅ test_env_override passed")


def test_credentials_path():
    """Test credentials path resolution"""
    from config import CREDENTIALS_PATH
    
    # Just check the path is a Path object and not empty
    assert isinstance(CREDENTIALS_PATH, Path)
    assert str(CREDENTIALS_PATH) != ""
    
    # In CI/Docker, file might not exist - that's ok
    # In local dev, it should exist
    if CREDENTIALS_PATH.exists():
        print(f"  Credentials found: {CREDENTIALS_PATH}")
    else:
        print(f"  Credentials NOT found (ok for CI): {CREDENTIALS_PATH}")
    
    print("✅ test_credentials_path passed")


if __name__ == "__main__":
    test_config_loads()
    test_env_override()
    test_credentials_path()
    print("\n✅ All config tests passed")
