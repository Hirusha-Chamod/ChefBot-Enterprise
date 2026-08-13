"""
Semantic Cache — Two-Layer Architecture
========================================
L1: In-process SHA-256 dict  (exact match, <1ms, lost on restart)
L2: pgvector in Neon DB      (cosine similarity, ~50ms, fully persistent)

Embedding model: all-MiniLM-L6-v2 (384-dim, CPU-only, no API cost)
Similarity threshold: 0.92  (catches rephrasing / minor wording differences)
"""

import os
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Constants                                                           #
# ------------------------------------------------------------------ #
SIMILARITY_THRESHOLD = 0.92   # Cosine similarity floor for a cache hit
EMBED_DIM = 384               # all-MiniLM-L6-v2 output dimension

# ------------------------------------------------------------------ #
#  L1: In-Memory Exact-Match Cache (hot path)                          #
# ------------------------------------------------------------------ #
_L1_CACHE: dict[str, str] = {}


def _make_l1_key(prompt: str, dietary: str, allow_web: bool) -> str:
    """SHA-256 key over normalised prompt + dietary + web flag."""
    key_str = f"{prompt.strip().lower()}:{dietary}:{allow_web}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ #
#  Embedding model — loaded once at first use (lazy singleton)         #
# ------------------------------------------------------------------ #
_embed_model = None


def _get_embed_model():
    """Lazy-load the sentence-transformer model (downloads on first run)."""
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[Cache] Loaded embedding model: all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"[Cache] sentence-transformers not available: {e}")
            _embed_model = False   # Mark as unavailable so we don't retry
    return _embed_model if _embed_model else None


def _embed(text: str) -> Optional[list]:
    """Returns a 384-dim embedding list, or None if model unavailable."""
    model = _get_embed_model()
    if model is None:
        return None
    try:
        vec = model.encode(text.strip().lower(), normalize_embeddings=True)
        return vec.tolist()
    except Exception as e:
        logger.warning(f"[Cache] Embedding failed: {e}")
        return None


# ------------------------------------------------------------------ #
#  L2: pgvector Neon DB helpers                                        #
# ------------------------------------------------------------------ #
def _is_postgres() -> bool:
    """Returns True when the app is connected to PostgreSQL."""
    try:
        from app.core.config import settings
        return bool(settings.DATABASE_URL and "postgresql" in settings.DATABASE_URL)
    except Exception:
        return False


def _get_pg_conn():
    """Opens a raw psycopg connection (not via the shared helper to avoid circular imports)."""
    try:
        import psycopg
        from psycopg.rows import dict_row
        from app.core.config import settings
        return psycopg.connect(settings.DATABASE_URL, row_factory=dict_row)
    except Exception:
        return None


def _pgvector_lookup(prompt: str, dietary: str, allow_web: bool) -> Optional[str]:
    """
    Queries Neon DB for a semantically similar cached response.
    Returns the cached response string, or None on miss.
    """
    embedding = _embed(prompt)
    if embedding is None:
        return None

    conn = _get_pg_conn()
    if conn is None:
        return None

    try:
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, response,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM   semantic_cache
                WHERE  dietary    = %s
                  AND  web_search = %s
                  AND  1 - (embedding <=> %s::vector) >= %s
                ORDER  BY similarity DESC
                LIMIT  1
                """,
                (vec_str, dietary, allow_web, vec_str, SIMILARITY_THRESHOLD),
            )
            row = cur.fetchone()
            if row:
                # Bump hit counter + last_hit_at
                cur.execute(
                    "UPDATE semantic_cache SET hit_count = hit_count + 1, last_hit_at = NOW() WHERE id = %s",
                    (row["id"],),
                )
                conn.commit()
                sim_pct = round(row["similarity"] * 100, 1)
                return f"[SEMANTIC CACHE HIT — {sim_pct}% match | $0 cost]\n\n{row['response']}"
    except Exception as e:
        logger.warning(f"[Cache] pgvector lookup failed: {e}")
    finally:
        conn.close()

    return None


def _pgvector_store(prompt: str, response: str, dietary: str, allow_web: bool):
    """Inserts a new entry into the Neon DB semantic cache."""
    embedding = _embed(prompt)
    if embedding is None:
        return

    conn = _get_pg_conn()
    if conn is None:
        return

    try:
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO semantic_cache (prompt_text, dietary, web_search, embedding, response)
                VALUES (%s, %s, %s, %s::vector, %s)
                ON CONFLICT DO NOTHING
                """,
                (prompt.strip().lower(), dietary, allow_web, vec_str, response),
            )
        conn.commit()
        logger.info("[Cache] Stored new entry in pgvector semantic cache.")
    except Exception as e:
        logger.warning(f"[Cache] pgvector store failed: {e}")
    finally:
        conn.close()


# ------------------------------------------------------------------ #
#  Public API (same signatures as before — no changes needed in        #
#  chat.py or any other caller)                                        #
# ------------------------------------------------------------------ #

def get_cached_recipe(prompt: str, dietary: str = "Standard", allow_web: bool = True) -> Optional[str]:
    """
    Two-layer cache lookup.

    1. L1 — exact SHA-256 in-memory dict   → <1ms
    2. L2 — pgvector cosine similarity      → ~50ms
    Returns None on a full miss.
    """
    # L1 — exact in-process hit
    l1_key = _make_l1_key(prompt, dietary, allow_web)
    if l1_key in _L1_CACHE:
        return f"[SEMANTIC CACHE HIT — 100% match | $0 cost]\n\n{_L1_CACHE[l1_key]}"

    # L2 — pgvector semantic similarity
    if _is_postgres():
        return _pgvector_lookup(prompt, dietary, allow_web)

    return None


def clean_recipe_response(text: str) -> str:
    """Strips intermediate LLM thoughts, search commentary, or cache headers from recipe text."""
    if not text:
        return ""

    clean_text = text

    # Strip any cache hit headers
    if "[SEMANTIC CACHE HIT" in clean_text:
        parts = clean_text.split("\n\n", 1)
        if len(parts) > 1:
            clean_text = parts[1]

    # If response contains '### Options Found:' or similar markers,
    # trim any preceding commentary (e.g. "Let me try a search... The search tools are returning empty...")
    for marker in ["### Options Found", "Options Found:", "### Option A", "1. **Option A:"]:
        if marker in clean_text:
            idx = clean_text.find(marker)
            if idx > 0:
                clean_text = clean_text[idx:]
            break

    return clean_text.strip()


def set_cached_recipe(prompt: str, recipe: str, dietary: str = "Standard", allow_web: bool = True):
    """
    Stores a recipe in both cache layers.
    Skips caching if the recipe contains a security alert or is empty.
    """
    if not prompt or not recipe or "[SECURITY ALERT]" in recipe:
        return

    # Clean recipe text to remove intermediate thoughts/commentary before saving
    clean_recipe = clean_recipe_response(recipe)
    if not clean_recipe:
        return

    # L1 — in-process
    l1_key = _make_l1_key(prompt, dietary, allow_web)
    _L1_CACHE[l1_key] = clean_recipe

    # L2 — pgvector (fire and forget; failures are logged, not raised)
    if _is_postgres():
        _pgvector_store(prompt, clean_recipe, dietary, allow_web)
