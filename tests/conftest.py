"""Test fixtures shared across all tests.

Sets dummy env vars before any module imports config.py — without this,
config import fails because real credentials aren't set in CI/dev.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("MASTODON_ACCESS_TOKEN", "test_token")
os.environ.setdefault("MASTODON_CLIENT_ID", "test_client_id")
os.environ.setdefault("MASTODON_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("MASTODON_API_BASE_URL", "https://test.example")
os.environ.setdefault("BOT_ACCOUNT_ID", "1")
os.environ.setdefault("GIPHY_API_KEY", "test_giphy_key")
os.environ.setdefault("LOCAL_GIFS_DIR", "/tmp/giphy-bot-test-gifs")
os.environ.setdefault("ADMIN_ACCT", "admin")

# Ensure project root is on sys.path so tests can import modules directly
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
