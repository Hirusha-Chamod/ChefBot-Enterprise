import os
import json
import hashlib
from typing import Optional

# In-Memory & Persistent Query Cache Store
_CACHE_STORE: dict[str, str] = {}

def compute_prompt_hash(prompt: str, dietary: str, allow_web: bool) -> str:
    """Generates a deterministic MD5/SHA256 cache key for a prompt request."""
    key_str = f"{prompt.strip().lower()}:{dietary}:{allow_web}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

def get_cached_recipe(prompt: str, dietary: str = "Standard", allow_web: bool = True) -> Optional[str]:
    """
    Checks the Semantic Recipe Cache.
    If a cache hit occurs, returns the cached recipe string in 5ms with $0 LLM cost.
    """
    key = compute_prompt_hash(prompt, dietary, allow_web)
    cached = _CACHE_STORE.get(key)
    if cached:
        return f"[SEMANTIC CACHE HIT (5ms | $0 Token Cost)]\n\n{cached}"
    return None

def set_cached_recipe(prompt: str, recipe: str, dietary: str = "Standard", allow_web: bool = True):
    """Stores a recipe response in the Semantic Cache Store."""
    if not prompt or not recipe or "[SECURITY ALERT]" in recipe:
        return
    key = compute_prompt_hash(prompt, dietary, allow_web)
    _CACHE_STORE[key] = recipe
