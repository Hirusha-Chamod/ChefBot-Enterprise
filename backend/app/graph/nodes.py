import os
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.graph.state import ChefBotState
from app.graph.tools import ALL_TOOLS, web_search, search_recipes_api, get_recipe_details, substitute_ingredient, calculate_nutrition

# Initialize LangChain ChatOpenAI configured for OpenRouter
def get_llm():
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=1500,
        temperature=0.7,
    )

def chefbot_agent_node(state: ChefBotState) -> Dict[str, Any]:
    """
    Core Agent Node in LangGraph.
    Inspects user prompt, dietary profile, and executes LLM completion.
    """
    dietary_profile = state.get("dietary_profile", "Standard")
    allow_web = state.get("allow_web_search", True)

    # Filter active tools based on allow_web_search
    if allow_web:
        active_tools = ALL_TOOLS
    else:
        active_tools = [t for t in ALL_TOOLS if t.name != "web_search"]

    system_prompt = (
        "You are ChefBot-Enterprise, a production-grade culinary AI agent.\n\n"
        "STRICT DOMAIN GUARDRAILS:\n"
        "1. You must ONLY answer questions directly related to food, cooking, recipes, ingredients, and nutrition.\n"
        "2. If the user asks off-topic questions (e.g. general trivia, geography, politics, sports, coding), "
        "DO NOT call any search tools or web search. Immediately respond politely stating that you are ChefBot.\n\n"
        f"USER DIETARY PROFILE: {dietary_profile.upper()}\n"
        "Strictly ensure all suggested ingredients and substitutes comply with this dietary restriction!\n\n"
        "OPERATIONAL INSTRUCTIONS:\n"
        "- Reason step-by-step using a ReAct loop.\n"
        "- Respect kitchen equipment constraints.\n"
        "- Use tools to search recipes and find ingredient substitutes.\n"
        "- MANDATORY: You MUST call `calculate_nutrition` for the final ingredient list before presenting your final recipe.\n"
        "- Present a clear, structured, appetizing recipe with macro totals at the end."
    )

    llm = get_llm().bind_tools(active_tools)
    
    # Inject system prompt at head of messages if not already present
    messages = list(state["messages"])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, SystemMessage(content=system_prompt))
    else:
        messages[0] = SystemMessage(content=system_prompt)

    response = llm.invoke(messages)
    return {"messages": [response]}

# Prebuilt LangGraph ToolNode for executing tool calls
tools_execution_node = ToolNode(ALL_TOOLS)
