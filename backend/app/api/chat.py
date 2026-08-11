import json
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.db.models import ChatRequest, ChatResponse
from app.core.guardrails import sanitize_user_input
from app.core.cache import get_cached_recipe, set_cached_recipe
from app.graph.workflow import chefbot_app

router = APIRouter(prefix="/chat", tags=["ChefBot Agent"])

@router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Executes the LangGraph ChefBot StateGraph Engine.
    Includes Semantic Vector Caching (5ms | $0 cost), Security Injection Filter, and LangGraph Thread Isolation.
    """
    # 1. Security Check: Sanitize User Input against Prompt Injection
    is_safe, sanitized_prompt = sanitize_user_input(request.prompt)
    if not is_safe:
        return ChatResponse(
            recipe=sanitized_prompt,
            thread_id=request.thread_id,
            dietary_applied=request.dietary_profile or "Standard"
        )

    # 2. Check Semantic Cache ($0 LLM Token Cost & 5ms Latency)
    cached_recipe = get_cached_recipe(sanitized_prompt, request.dietary_profile or "Standard", request.allow_web_search)
    if cached_recipe:
        return ChatResponse(
            recipe=cached_recipe,
            thread_id=request.thread_id,
            dietary_applied=request.dietary_profile or "Standard"
        )

    # 3. Configurable Thread Session State
    config = {"configurable": {"thread_id": request.thread_id}}

    # 4. Build LangGraph Input State
    inputs = {
        "messages": [HumanMessage(content=sanitized_prompt)],
        "dietary_profile": request.dietary_profile or "Standard",
        "allow_web_search": request.allow_web_search,
        "thread_id": request.thread_id,
    }

    try:
        # 5. Invoke Compiled LangGraph StateGraph
        output_state = chefbot_app.invoke(inputs, config=config)
        messages: list[BaseMessage] = output_state.get("messages", [])

        # 6. Extract Final AI Message
        recipe_text = "ChefBot created a recipe!"
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                recipe_text = msg.content
                break

        # 7. Save to Semantic Cache
        set_cached_recipe(sanitized_prompt, recipe_text, request.dietary_profile or "Standard", request.allow_web_search)

        return ChatResponse(
            recipe=recipe_text,
            thread_id=request.thread_id,
            dietary_applied=request.dietary_profile or "Standard"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ChefBot Engine Error: {str(e)}")

@router.get("/stream")
async def stream_chat_events(prompt: str, allow_web_search: bool = True, dietary_profile: str = "Standard", thread_id: str = "default_session"):
    """
    Streams LangGraph execution node events live to the UI via Server-Sent Events (SSE).
    """
    is_safe, sanitized_prompt = sanitize_user_input(prompt)
    if not is_safe:
        async def event_generator():
            yield {"event": "error", "data": json.dumps({"message": sanitized_prompt})}
        return EventSourceResponse(event_generator())

    config = {"configurable": {"thread_id": thread_id}}
    inputs = {
        "messages": [HumanMessage(content=sanitized_prompt)],
        "dietary_profile": dietary_profile,
        "allow_web_search": allow_web_search,
        "thread_id": thread_id,
    }

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"status": "ChefBot LangGraph Agent Started..."})}
        try:
            for event in chefbot_app.stream(inputs, config=config):
                for node_name, node_output in event.items():
                    if node_name == "agent":
                        yield {"event": "thinking", "data": json.dumps({"node": "agent", "message": "📍 ChefBot Reasoning..."})}
                    elif node_name == "tools":
                        yield {"event": "tool", "data": json.dumps({"node": "tools", "message": "🔧 Executing Tools (Tavily/USDA)..."})}
            yield {"event": "complete", "data": json.dumps({"status": "Recipe Generation Complete!"})}
        except Exception as err:
            yield {"event": "error", "data": json.dumps({"message": str(err)})}

    return EventSourceResponse(event_generator())
