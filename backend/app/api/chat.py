import json
import asyncio
import queue
import threading
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.db.models import ChatRequest, ChatResponse, SessionResponse, HistoryResponse, MessageItem
from app.db.database import get_db_connection, _is_postgres, release_db_connection
from app.core.guardrails import sanitize_user_input
from app.core.cache import get_cached_recipe, set_cached_recipe
from app.core.security import decode_access_token
from app.graph.workflow import chefbot_app

router = APIRouter(prefix='/chat', tags=['ChefBot Agent'])

def _ph() -> str:
    """Returns the correct SQL placeholder for the active DB driver."""
    return "%s" if _is_postgres() else "?"


def get_optional_user_id(authorization: Optional[str] = Header(None)) -> Optional[int]:
    """Helper to decode user_id if valid Bearer token is provided."""
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None

    ph = _ph()
    conn = get_db_connection()
    user_id = None
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute(f"SELECT id FROM users WHERE username = {ph}", (payload["sub"],))
                user = cur.fetchone()
                user_id = user["id"] if user else None
        else:
            user = conn.execute(f"SELECT id FROM users WHERE username = {ph}", (payload["sub"],)).fetchone()
            user_id = user["id"] if user else None
    finally:
        release_db_connection(conn)
    return user_id


_SESSIONS_CACHE: dict = {}

def invalidate_sessions_cache():
    global _SESSIONS_CACHE
    _SESSIONS_CACHE.clear()


def record_chat_session(thread_id: str, prompt: str, user_id: Optional[int] = None):
    """Inserts or updates a session entry in the database."""
    invalidate_sessions_cache()
    ph = _ph()
    ts_fn = "NOW()" if _is_postgres() else "CURRENT_TIMESTAMP"
    conn = get_db_connection()
    title_text = (prompt[:35] + "...") if len(prompt) > 35 else prompt

    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute(f"SELECT id FROM chat_sessions WHERE thread_id = {ph}", (thread_id,))
                existing = cur.fetchone()
                if existing:
                    if user_id:
                        cur.execute(
                            f"UPDATE chat_sessions SET updated_at = {ts_fn}, user_id = {ph} WHERE thread_id = {ph}",
                            (user_id, thread_id)
                        )
                    else:
                        cur.execute(
                            f"UPDATE chat_sessions SET updated_at = {ts_fn} WHERE thread_id = {ph}",
                            (thread_id,)
                        )
                else:
                    cur.execute(
                        f"INSERT INTO chat_sessions (thread_id, user_id, title) VALUES ({ph}, {ph}, {ph})",
                        (thread_id, user_id, title_text)
                    )
        else:
            cursor = conn.cursor()
            existing = cursor.execute(
                f"SELECT id FROM chat_sessions WHERE thread_id = {ph}", (thread_id,)
            ).fetchone()
            if existing:
                if user_id:
                    cursor.execute(
                        f"UPDATE chat_sessions SET updated_at = {ts_fn}, user_id = {ph} WHERE thread_id = {ph}",
                        (user_id, thread_id)
                    )
                else:
                    cursor.execute(
                        f"UPDATE chat_sessions SET updated_at = {ts_fn} WHERE thread_id = {ph}",
                        (thread_id,)
                    )
            else:
                cursor.execute(
                    f"INSERT INTO chat_sessions (thread_id, user_id, title) VALUES ({ph}, {ph}, {ph})",
                    (thread_id, user_id, title_text)
                )
            conn.commit()
    finally:
        release_db_connection(conn)

@router.post('', response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, authorization: Optional[str] = Header(None)):
    user_id = get_optional_user_id(authorization)
    print(f"\n==========================================")
    print(f"[API REQUEST /chat] Prompt: \"{request.prompt}\"")
    print(f"[API PARAMS] Allow Web Search: {request.allow_web_search} | Dietary: {request.dietary_profile} | Servings: {request.servings} | Thread: {request.thread_id}")
    print(f"==========================================")
    
    is_safe, sanitized_prompt = sanitize_user_input(request.prompt)
    if not is_safe:
        return ChatResponse(
            recipe=sanitized_prompt,
            thread_id=request.thread_id,
            dietary_applied=request.dietary_profile or 'Standard',
            servings_applied=request.servings
        )

    record_chat_session(request.thread_id, request.prompt, user_id)

    cached_recipe = get_cached_recipe(f'{sanitized_prompt}:servings_{request.servings}', request.dietary_profile or 'Standard', request.allow_web_search)
    if cached_recipe:
        print(f"[API RESPONSE /chat] Returning Cached Response ({len(cached_recipe)} chars)!")
        config = {'configurable': {'thread_id': request.thread_id}}
        try:
            chefbot_app.update_state(config, {
                'messages': [
                    HumanMessage(content=sanitized_prompt),
                    AIMessage(content=cached_recipe)
                ]
            })
            print(f"[CACHE SYNC] State synced to LangGraph checkpointer for thread {request.thread_id}")
        except Exception as sync_err:
            print(f"[CACHE SYNC WARN] State sync failed: {sync_err}")

        return ChatResponse(
            recipe=cached_recipe,
            thread_id=request.thread_id,
            dietary_applied=request.dietary_profile or 'Standard',
            servings_applied=request.servings
        )

    config = {'configurable': {'thread_id': request.thread_id}}
    inputs = {
        'messages': [HumanMessage(content=sanitized_prompt)],
        'dietary_profile': request.dietary_profile or 'Standard',
        'allow_web_search': request.allow_web_search,
        'thread_id': request.thread_id,
        'servings': request.servings,
    }

    try:
        output_state = chefbot_app.invoke(inputs, config=config)
        messages: list[BaseMessage] = output_state.get('messages', [])

        recipe_text = 'ChefBot created a recipe!'
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                recipe_text = str(msg.content)
                break

        set_cached_recipe(f'{sanitized_prompt}:servings_{request.servings}', recipe_text, request.dietary_profile or 'Standard', request.allow_web_search)

        return ChatResponse(
            recipe=recipe_text,
            thread_id=request.thread_id,
            dietary_applied=request.dietary_profile or 'Standard',
            servings_applied=request.servings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'ChefBot Engine Error: {str(e)}')

@router.post('/stream')
async def chat_stream_endpoint(request: ChatRequest, authorization: Optional[str] = Header(None)):
    user_id = get_optional_user_id(authorization)
    print(f"\n==========================================")
    print(f"[API REQUEST /chat/stream] Prompt: \"{request.prompt}\"")
    print(f"[API PARAMS] Allow Web Search: {request.allow_web_search} | Dietary: {request.dietary_profile} | Servings: {request.servings} | Thread: {request.thread_id}")
    print(f"==========================================")
    
    is_safe, sanitized_prompt = sanitize_user_input(request.prompt)
    if not is_safe:
        async def safe_gen():
            yield {"data": json.dumps({"token": sanitized_prompt, "done": True})}
        return EventSourceResponse(safe_gen())

    record_chat_session(request.thread_id, request.prompt, user_id)

    cached_recipe = get_cached_recipe(f'{sanitized_prompt}:servings_{request.servings}', request.dietary_profile or 'Standard', request.allow_web_search)
    if cached_recipe:
        print(f"[API RESPONSE /chat/stream] Returning Cached Response ({len(cached_recipe)} chars)!")
        config = {'configurable': {'thread_id': request.thread_id}}
        try:
            chefbot_app.update_state(config, {
                'messages': [
                    HumanMessage(content=sanitized_prompt),
                    AIMessage(content=cached_recipe)
                ]
            })
            print(f"[CACHE SYNC] State synced to LangGraph checkpointer for thread {request.thread_id}")
        except Exception as sync_err:
            print(f"[CACHE SYNC WARN] State sync failed: {sync_err}")

        async def cached_gen():
            yield {"data": json.dumps({"token": cached_recipe, "done": False})}
            yield {"data": json.dumps({"token": "", "done": True})}
        return EventSourceResponse(cached_gen())

    config = {'configurable': {'thread_id': request.thread_id}}
    inputs = {
        'messages': [HumanMessage(content=sanitized_prompt)],
        'dietary_profile': request.dietary_profile or 'Standard',
        'allow_web_search': request.allow_web_search,
        'thread_id': request.thread_id,
        'servings': request.servings,
    }

    q = queue.Queue()

    def stream_worker():
        try:
            for chunk in chefbot_app.stream(inputs, config=config, stream_mode="messages"):
                if chunk and len(chunk) > 0:
                    msg_obj = chunk[0]
                    if hasattr(msg_obj, "content") and msg_obj.content:
                        content_str = str(msg_obj.content)
                        if content_str and isinstance(msg_obj, AIMessage) and not getattr(msg_obj, "tool_calls", None):
                            q.put({"token": content_str})
            q.put({"done": True})
        except Exception as err:
            q.put({"error": str(err)})

    threading.Thread(target=stream_worker, daemon=True).start()

    async def event_generator():
        accumulated_text = ""
        while True:
            try:
                item = await asyncio.to_thread(q.get, True, 0.1)
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue

            if "error" in item:
                yield {"data": json.dumps({"error": item["error"], "done": True})}
                break

            if item.get("done"):
                final_recipe_text = ""
                try:
                    state = chefbot_app.get_state(config)
                    msgs = state.values.get("messages", []) if state and state.values else []
                    for m in reversed(msgs):
                        if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                            final_recipe_text = str(m.content)
                            break
                except Exception:
                    pass

                text_to_cache = final_recipe_text or accumulated_text
                if text_to_cache:
                    set_cached_recipe(f'{sanitized_prompt}:servings_{request.servings}', text_to_cache, request.dietary_profile or 'Standard', request.allow_web_search)
                
                yield {"data": json.dumps({"token": "", "done": True})}
                break

            token = item.get("token", "")
            if token:
                accumulated_text += token
                yield {"data": json.dumps({"token": token, "done": False})}

    return EventSourceResponse(event_generator())

@router.get('/sessions', response_model=List[SessionResponse])
def get_sessions(authorization: Optional[str] = Header(None)):
    user_id = get_optional_user_id(authorization)
    cache_key = f"user_{user_id}"
    now = time.time()

    if cache_key in _SESSIONS_CACHE:
        ts, cached_data = _SESSIONS_CACHE[cache_key]
        if now - ts < 10:  # 10 second TTL
            return cached_data

    ph = _ph()
    conn = get_db_connection()

    try:
        if _is_postgres():
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        f"SELECT id, thread_id, user_id, title, CAST(created_at AS TEXT) AS created_at, CAST(updated_at AS TEXT) AS updated_at FROM chat_sessions WHERE user_id = {ph} OR user_id IS NULL ORDER BY updated_at DESC LIMIT 50",
                        (user_id,)
                    )
                else:
                    cur.execute(
                        "SELECT id, thread_id, user_id, title, CAST(created_at AS TEXT) AS created_at, CAST(updated_at AS TEXT) AS updated_at FROM chat_sessions WHERE user_id IS NULL ORDER BY updated_at DESC LIMIT 20"
                    )
                result = [dict(r) for r in cur.fetchall()]
        else:
            if user_id:
                rows = conn.execute(
                    f"SELECT id, thread_id, user_id, title, created_at, updated_at FROM chat_sessions WHERE user_id = {ph} OR user_id IS NULL ORDER BY updated_at DESC LIMIT 50",
                    (user_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, thread_id, user_id, title, created_at, updated_at FROM chat_sessions WHERE user_id IS NULL ORDER BY updated_at DESC LIMIT 20"
                ).fetchall()
            result = [dict(row) for row in rows]

        _SESSIONS_CACHE[cache_key] = (now, result)
        return result
    finally:
        release_db_connection(conn)

@router.get('/history/{thread_id}', response_model=HistoryResponse)
def get_session_history(thread_id: str):
    config = {'configurable': {'thread_id': thread_id}}
    try:
        state = chefbot_app.get_state(config)
        messages = state.values.get('messages', []) if state and state.values else []
        
        parsed_history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                parsed_history.append(MessageItem(role="user", content=str(msg.content)))
            elif isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                parsed_history.append(MessageItem(role="assistant", content=str(msg.content)))

        return HistoryResponse(thread_id=thread_id, messages=parsed_history)
    except Exception as e:
        return HistoryResponse(thread_id=thread_id, messages=[])

@router.delete('/sessions/{thread_id}')
def delete_session(thread_id: str):
    invalidate_sessions_cache()
    ph = _ph()
    conn = get_db_connection()
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM chat_sessions WHERE thread_id = {ph}", (thread_id,))
        else:
            conn.execute(f"DELETE FROM chat_sessions WHERE thread_id = {ph}", (thread_id,))
            conn.commit()
    finally:
        release_db_connection(conn)
    return {"status": "success", "message": f"Session {thread_id} deleted."}
