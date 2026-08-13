import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.graph.state import ChefBotState
from app.graph.tools import ALL_TOOLS

def chefbot_agent_node(state: ChefBotState) -> dict:
    messages = state.get("messages", [])
    dietary = state.get("dietary_profile", "Standard")
    servings = state.get("servings", 2)
    allow_web_search = state.get("allow_web_search", True)

    # Extract last user prompt for logging
    last_user_prompt = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human":
            last_user_prompt = str(msg.content)
            break

    print(f"\n[AGENT NODE] Incoming Prompt: \"{last_user_prompt}\"")
    print(f"[AGENT CONFIG] Dietary: {dietary} | Servings: {servings} | Allow Web Search: {allow_web_search}")

    summary_block = ""
    if len(messages) > 10:
        old_msgs = [msg.content for msg in messages[:-8] if hasattr(msg, "content")]
        summary_text = "; ".join(old_msgs[-3:])
        summary_block = f"\n\n[LANGMEM CONVERSATION SUMMARY]:\n- recent user preferences: {summary_text}"
        messages = messages[-8:]

    sys_prompt = (
        "YOU ARE CHEFBOT - AN ENTERPRISE CULINARY AI ASSISTANT.\n\n"
        "RULE 1: You MUST only answer culinary, recipe, ingredient, or kitchen-related questions.\n"
        "IF any off-topic question is asked, IMMEDIATELY REJECT WITH:\n"
        "\"I am ChefBot, your culinary assistant. I can only help you with cooking, recipes, and food.\"\n\n"
        f"USER DIETARY PROFILE: {dietary}.\n"
        "ADJUST ALL RECIPES TO STRICTLY HONOR THIS DIETARY PROFILE!\n\n"
        f"USER REQUESTED SERVINGS: {servings} PEOPLE.\n"
        f"SCALE ALL INGREDIENT QUANTITIES, PAN SIZES, AND USDA NUTRITION TOTALS PROPORTIONALLY FOR {servings} SERVINGS!\n\n"
        f"WEB SEARCH ALLOWED: {allow_web_search}.\n"
        + ("Do NOT attempt web search; rely on your internal culinary knowledge and database tools.\n\n" if not allow_web_search else "\n") +
        "EFFICIENCY RULE: Be fast and decisive! Execute all necessary tools in parallel in as few turns as possible. Do NOT make duplicate search calls.\n\n"
        "FORMAT RULE: When a user asks for a recipe, provide 3 DISTINCT CANDIDATE OPTIONS and detailed step-by-step instructions for each option in this exact format:\n"
        "### Options Found:\n"
        "1. **Option A: [Recipe Name]** (~[Time] mins | [Kcal] kcal) - [1-line description]\n"
        "2. **Option B: [Recipe Name]** (~[Time] mins | [Kcal] kcal) - [1-line description]\n"
        "3. **Option C: [Recipe Name]** (~[Time] mins | [Kcal] kcal) - [1-line description]\n\n"
        "### Option A Steps\n"
        "Step 1: [Detailed preparation instruction with pan size and timer e.g. 'heat skillet for 2 minutes']\n"
        "Step 2: [Step instruction with timer e.g. 'cook eggs for 4 minutes']\n\n"
        "### Option B Steps\n"
        "Step 1: [Detailed preparation instruction with pan size and timer]\n"
        "Step 2: [Step instruction with timer]\n\n"
        "### Option C Steps\n"
        "Step 1: [Detailed preparation instruction with pan size and timer]\n"
        "Step 2: [Step instruction with timer]\n"
        f"{summary_block}"
    )

    llm = ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.2,
        max_tokens=1600,
    )

    # Filter tools based on allow_web_search setting
    active_tools = [t for t in ALL_TOOLS if (allow_web_search or t.name != "web_search")]
    tool_names = [t.name for t in active_tools]
    print(f"[AGENT TOOL BINDING] Active Tools Bound to LLM: {tool_names}")

    if active_tools:
        llm = llm.bind_tools(active_tools)

    sys_msg = SystemMessage(content=sys_prompt)
    full_messages = [sys_msg] + messages
    response = llm.invoke(full_messages)

    if getattr(response, "tool_calls", None):
        print(f"[AGENT DECISION] LLM requested {len(response.tool_calls)} tool call(s):")
        for tc in response.tool_calls:
            print(f"  -> Tool: {tc.get('name')} | Args: {tc.get('args')}")
    else:
        resp_snippet = str(response.content)[:120].replace('\n', ' ')
        print(f"[AGENT DECISION] LLM returned final text answer (no tools). Snippet: \"{resp_snippet}...\"")

    return {"messages": [response]}

tools_execution_node = ToolNode(ALL_TOOLS)
