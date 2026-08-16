import sqlite3
import os
import psycopg
from psycopg.rows import dict_row
from app.core.config import settings

# -----------------------------------------------------------------
# Connection helpers — PostgreSQL (Neon DB) preferred, SQLite fallback
# -----------------------------------------------------------------

import threading
import time

_POOL = None
_HEARTBEAT_STARTED = False


def _start_heartbeat():
    """Starts a daemon thread that pings Neon DB every 2 minutes to prevent cold starts."""
    global _HEARTBEAT_STARTED
    if _HEARTBEAT_STARTED:
        return
    _HEARTBEAT_STARTED = True

    def heartbeat_worker():
        while True:
            time.sleep(120)
            if _is_postgres():
                pool = get_db_pool()
                if pool:
                    try:
                        with pool.connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("SELECT 1;")
                    except Exception:
                        pass

    t = threading.Thread(target=heartbeat_worker, daemon=True)
    t.start()


def _is_postgres() -> bool:
    """Returns True when a valid PostgreSQL DATABASE_URL is configured."""
    return bool(settings.DATABASE_URL and "postgresql" in settings.DATABASE_URL)


def get_db_pool():
    """Lazy-initializes and returns a psycopg3 ConnectionPool for Neon DB."""
    global _POOL
    if _POOL is None and _is_postgres():
        try:
            from psycopg_pool import ConnectionPool
            _POOL = ConnectionPool(
                conninfo=settings.DATABASE_URL,
                min_size=1,
                max_size=10,
                max_idle=60.0,
                check=ConnectionPool.check_connection,
                kwargs={"row_factory": dict_row, "autocommit": True}
            )
            print("[INFO] Initialized Neon DB Connection Pool (min=2, max=10).")
            _start_heartbeat()
        except Exception as err:
            print(f"[WARN] ConnectionPool init failed: {err}")
    return _POOL


def get_db_connection():
    """
    Returns an open database connection.
    - If PostgreSQL and pool available: fetches a warm connection from pool.
    - Otherwise: returns a new psycopg or sqlite3 connection.
    """
    if _is_postgres():
        pool = get_db_pool()
        if pool:
            try:
                return pool.getconn()
            except Exception:
                pass
        return psycopg.connect(settings.DATABASE_URL, row_factory=dict_row)

    # SQLite fallback
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def release_db_connection(conn):
    """Releases a connection back to the pool or closes it."""
    if not conn:
        return
    if _is_postgres():
        pool = get_db_pool()
        if pool:
            try:
                pool.putconn(conn)
                return
            except Exception:
                pass
    try:
        conn.close()
    except Exception:
        pass


def init_db():
    """
    Creates the application schema (users, chat_sessions) in whichever
    database is active.  Safe to call multiple times (IF NOT EXISTS).
    """
    if _is_postgres():
        _init_postgres()
    else:
        _init_sqlite()


def _init_postgres():
    """Creates application tables and vector cache in Neon DB (PostgreSQL)."""
    conn = psycopg.connect(settings.DATABASE_URL, row_factory=dict_row)
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                dietary_profile TEXT DEFAULT 'Standard',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id SERIAL PRIMARY KEY,
                thread_id TEXT UNIQUE NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """)

            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Semantic cache table — stores prompt embeddings + responses
            cur.execute("""
            CREATE TABLE IF NOT EXISTS semantic_cache (
                id          SERIAL PRIMARY KEY,
                prompt_text TEXT        NOT NULL,
                dietary     TEXT        NOT NULL DEFAULT 'Standard',
                web_search  BOOLEAN     NOT NULL DEFAULT TRUE,
                embedding   vector(384),
                response    TEXT        NOT NULL,
                hit_count   INTEGER     NOT NULL DEFAULT 1,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                last_hit_at TIMESTAMPTZ DEFAULT NOW()
            );
            """)

            # HNSW index for fast cosine similarity search
            cur.execute("""
            CREATE INDEX IF NOT EXISTS semantic_cache_embedding_idx
            ON semantic_cache USING hnsw (embedding vector_cosine_ops);
            """)

    conn.close()
    print("[INFO] Neon DB schema initialised (users + chat_sessions + semantic_cache + hnsw index).")


def _init_sqlite():
    """Creates tables in the local SQLite file (dev / offline fallback)."""
    db_dir = os.path.dirname(settings.DB_PATH)
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        dietary_profile TEXT DEFAULT 'Standard',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT UNIQUE NOT NULL,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("[INFO] SQLite schema initialised (users + chat_sessions).")


# Auto-initialise on import
init_db()
