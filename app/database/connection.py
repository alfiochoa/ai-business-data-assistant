"""Lazy Postgres connection helper.

Reads DATABASE_URL from the environment (via python-dotenv) the first time a
connection is actually requested — never at import time — so this module can
be imported freely (e.g. by tests that mock everything below this layer)
without needing a real database or even a .env file present.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

_env_loaded = False


def _ensure_env_loaded() -> None:
    global _env_loaded
    if not _env_loaded:
        load_dotenv()
        _env_loaded = True


def get_database_url() -> str:
    _ensure_env_loaded()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill in "
            "your Supabase (or other Postgres) connection string."
        )
    return url


def get_connection() -> psycopg2.extensions.connection:
    """Open a new connection. Caller is responsible for closing it."""
    return psycopg2.connect(get_database_url())


@contextmanager
def get_cursor() -> Iterator[psycopg2.extras.RealDictCursor]:
    """Context manager yielding a dict-row cursor with commit/rollback handling."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
