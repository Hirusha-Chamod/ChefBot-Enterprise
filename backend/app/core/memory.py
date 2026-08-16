import os
import threading
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.store.memory import InMemoryStore
from langmem import create_memory_manager, create_manage_memory_tool, create_search_memory_tool
from app.core.config import settings

# Global Store for LangMem
_STORE = None

def get_memory_store():
    """Initializes and returns the LangGraph PostgresStore or InMemoryStore for LangMem."""
    global _STORE
    if _STORE is not None:
        return _STORE

    db_url = settings.DATABASE_URL
    if db_url and "postgresql" in db_url:
        try:
            from langgraph.store.postgres import PostgresStore
            from psycopg_pool import ConnectionPool
            pool = ConnectionPool(
                conninfo=db_url,
                min_size=1,
                max_size=5,
                max_idle=60.0,
                check=ConnectionPool.check_connection,
                kwargs={"autocommit": True}
            )
            _STORE = PostgresStore(pool)
            _STORE.setup()
            print("[INFO] LangMem PostgresStore connected & initialized in Neon DB.")
            return _STORE
        except Exception as err:
            print(f"[WARN] LangMem PostgresStore error: {err}. Falling back to InMemoryStore.")

    _STORE = InMemoryStore()
    print("[INFO] LangMem using InMemoryStore.")
    return _STORE


def get_memory_tools():
    """Returns the official LangMem search and manage memory tools."""
    store = get_memory_store()
    search_tool = create_search_memory_tool(
        namespace=("memories", "{user_id}"),
        store=store,
        instructions="Search persistent long-term culinary preferences, allergies, equipment, and family size."
    )
    manage_tool = create_manage_memory_tool(
        namespace=("memories", "{user_id}"),
        store=store,
        instructions="Record or update user culinary memories (allergies, taste preferences, kitchen equipment)."
    )
    return [search_tool, manage_tool]


def get_user_memories_text(user_id: str) -> str:
    """Retrieves all active memories for a given user from the LangMem store."""
    if not user_id:
        user_id = "default_user"
    store = get_memory_store()
    try:
        namespace = ("memories", str(user_id))
        memories = store.search(namespace, limit=10)
        if not memories:
            return ""
        lines = []
        for m in memories:
            val = m.value
            if isinstance(val, dict):
                text = val.get("content") or val.get("text") or val.get("memory") or str(val)
            else:
                text = str(val)
            lines.append(f"- {text}")
        return "\n".join(lines)
    except Exception as e:
        print(f"[WARN] Error fetching user memories from LangMem store: {e}")
        return ""


def extract_and_store_memories_async(messages: List[BaseMessage], user_id: str):
    """Runs LangMem memory manager in a background thread to extract durable facts."""
    if not user_id:
        user_id = "default_user"
    if len(messages) < 2:
        return

    def _worker():
        models_to_try = [
            "google/gemma-4-26b-a4b-it:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "liquid/lfm-2.5-2.6b:free"
        ]
        store = get_memory_store()
        
        for model_name in models_to_try:
            try:
                llm = ChatOpenAI(
                    model=model_name,
                    api_key=settings.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0.1,
                    max_tokens=400,
                    request_timeout=15.0
                )
                manager = create_memory_manager(
                    llm,
                    instructions=(
                        "You are a culinary memory manager. Extract durable user facts such as:\n"
                        "- Food allergies or intolerances\n"
                        "- Dietary preferences and dislikes\n"
                        "- Household size (number of people cooked for)\n"
                        "- Kitchen appliances and equipment\n"
                        "Do NOT remember temporary one-off recipe requests."
                    )
                )
                extracted = manager.invoke({"messages": messages})
                if extracted:
                    namespace = ("memories", str(user_id))
                    for item in extracted:
                        raw_content = getattr(item, "content", item)
                        mem_text = getattr(raw_content, "content", str(raw_content))
                        mem_id = getattr(item, "id", f"mem_{hash(mem_text) % 1000000}")
                        store.put(namespace, str(mem_id), {"text": mem_text, "user_id": str(user_id)})
                        print(f"[LANGMEM SAVED] Stored memory for user {user_id}: \"{mem_text}\"")
                break  # Successful extraction
            except Exception as err:
                print(f"[LANGMEM BACKGROUND WARN] Model {model_name} extraction failed: {err}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
