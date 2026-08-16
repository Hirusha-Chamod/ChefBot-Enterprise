import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.graph.state import ChefBotState
from app.graph.tools import ALL_TOOLS
from app.core.memory import get_memory_tools, get_user_memories_text

def chefbot_agent_node(state: ChefBotState) -> dict:
    messages = state.get("messages", [])
    dietary = state.get("dietary_profile", "Standard")
    servings = state.get("servings", 2)
    allow_web_search = state.get("allow_web_search", True)
    user_id = state.get("user_id", "default_user")

    # Extract last user prompt for logging
    last_user_prompt = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human":
            last_user_prompt = str(msg.content)
            break

    print(f"\n[AGENT NODE] Incoming Prompt: \"{last_user_prompt}\"")
    print(f"[AGENT CONFIG] Dietary: {dietary} | Servings: {servings} | Allow Web Search: {allow_web_search}")

    # Fetch persistent user memories from LangMem Store
    user_memories_text = get_user_memories_text(user_id)
    memory_block = ""
    if user_memories_text:
        memory_block = f"\n\n[PERSISTENT CULINARY MEMORY (LangMem)]:\n{user_memories_text}\nCRITICAL: Strictly adhere to these user preferences across all recommendations!"

    summary_block = ""
    if len(messages) > 10:
        old_msgs = [msg.content for msg in messages[:-8] if hasattr(msg, "content")]
        summary_text = "; ".join(old_msgs[-3:])
        summary_block = f"\n\n[CONVERSATION SUMMARY]:\n- recent user preferences: {summary_text}"
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
        "EFFICIENCY RULE: Be fast and decisive! Execute search and calculate_nutrition tools in parallel during Turn 1 whenever possible. If search returns no matches, IMMEDIATELY formulate recipes from your culinary knowledge and calculate nutrition in Turn 2. DO NOT make repeated search attempts. Complete requests in 2 agent turns maximum.\n\n"
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
        f"{memory_block}"
    )

    primary_model = settings.OPENROUTER_MODEL or "google/gemma-4-26b-a4b-it:free"
    candidate_models = [
        primary_model,
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "nvidia/nemotron-3.5-lightning:free",
        "liquid/lfm-2.5-2.6b:free",
    ]
    seen = set()
    unique_models = [m for m in candidate_models if not (m in seen or seen.add(m))]

    active_tools = [t for t in ALL_TOOLS if (allow_web_search or t.name != "web_search")] + get_memory_tools()
    tool_names = [t.name for t in active_tools]
    print(f"[AGENT TOOL BINDING] Active Tools Bound to LLM: {tool_names}")

    sys_msg = SystemMessage(content=sys_prompt)
    full_messages = [sys_msg] + messages

    response = None
    last_err = None

    for model_name in unique_models:
        try:
            llm = ChatOpenAI(
                model=model_name,
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.2,
                max_tokens=1200,
                request_timeout=15.0,
                streaming=True,
            )
            if active_tools:
                llm = llm.bind_tools(active_tools)

            response = None
            for chunk in llm.stream(full_messages):
                response = chunk if response is None else response + chunk

            if model_name != primary_model:
                print(f"[AGENT MODEL FALLBACK SUCCESS] Model '{model_name}' succeeded.")
            break
        except Exception as err:
            print(f"[AGENT MODEL WARN] Model '{model_name}' timed out or errored: {err}. Trying next free model...")
            last_err = err

    if not response:
        raise RuntimeError(f"All LLM candidate models failed. Last error: {last_err}")

    if getattr(response, "tool_calls", None):
        print(f"[AGENT DECISION] LLM requested {len(response.tool_calls)} tool call(s):")
        for tc in response.tool_calls:
            print(f"  -> Tool: {tc.get('name')} | Args: {tc.get('args')}")
    else:
        resp_snippet = str(response.content)[:120].replace('\n', ' ')
        print(f"[AGENT DECISION] LLM returned final text answer (no tools). Snippet: \"{resp_snippet}...\"")

    return {"messages": [response]}

tools_execution_node = ToolNode(ALL_TOOLS + get_memory_tools())
