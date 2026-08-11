from fastapi import APIRouter, HTTPException, Depends
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.db.models import ChatRequest, ChatResponse
from app.core.guardrails import sanitize_user_input
from app.graph.workflow import chefbot_app

router = APIRouter(prefix="/chat", tags=["ChefBot Agent"])

@router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Executes the LangGraph ChefBot StateGraph Engine.
    Includes Security Prompt Injection Sanitizer, Dietary Profiles, and Thread Persistence.
    """
    # 1. Security Check: Sanitize User Input against Prompt Injection
    is_safe, sanitized_prompt = sanitize_user_input(request.prompt)
    if not is_safe:
        return ChatResponse(
            recipe=sanitized_prompt,
            thread_id=request.thread_id,
            dietary_applied=request.dietary_profile or "Standard"
        )

    # 2. Configurable Thread Session State
    config = {"configurable": {"thread_id": request.thread_id}}

    # 3. Build LangGraph Input State
    inputs = {
        "messages": [HumanMessage(content=sanitized_prompt)],
        "dietary_profile": request.dietary_profile or "Standard",
        "allow_web_search": request.allow_web_search,
        "thread_id": request.thread_id,
    }

    try:
        # 4. Invoke Compiled LangGraph StateGraph
        output_state = chefbot_app.invoke(inputs, config=config)
        messages: list[BaseMessage] = output_state.get("messages", [])

        # 5. Extract Final AI Message
        recipe_text = "ChefBot created a recipe!"
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                recipe_text = msg.content
                break

        return ChatResponse(
            recipe=recipe_text,
            thread_id=request.thread_id,
            dietary_applied=request.dietary_profile or "Standard"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ChefBot Engine Error: {str(e)}")
