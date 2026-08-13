import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.graph.state import ChefBotState
from app.graph.tools import ALL_TOOLS

def chefbot_agent_node(state: ChefBotState) -> dict:
    messages = state.get('messages', [])
    dietary = state.get('dietary_profile', 'Standard')
    servings = state.get('servings', 2)

    summary_block = ''
    if len(messages) > 10:
        old_msgs = [msg.content for msg in messages[:-8] if hasattr(msg, 'content')]
        summary_text = '; '.join(old_msgs[-3:])
        summary_block = f'\n\n[LANGMEM CONVERSATION SUMMARY]:\n- recent user preferences: {summary_text}'
        messages = messages[-8:]

    sys_prompt = (
        'YOU ARE CHEFBOT - AN ENTERPRISE CULINARY AI ASSISTANT.\n\n'
        'RULE 1: You MUST only answer culinary, recipe, ingredient, or kitchen-related questions.\n'
        'IF any off-topic question is asked, IMMEDIATELY REJECT WITH:\n'
        '" I am ChefBot your culinary assistant. I can only help you with cooking recipes and food.\\n\n'
 f'USER DIETARY PROFILE: {dietary}.\n'
 'ADJUST ALL RECIPES TO STRICTLY HONOR THIS DIETARY PROFILE!\n\n'
 f'USER REQUESTED SERVINGS: {servings} PEOPLE.\n'
 f'SCALE ALL INGREDIENT QUANTITIES, PAN SIZES, AND USDA NUTRITION TOTALS PROPORTIONALLY FOR {servings} SERVINGS!\n\n'
 'FORMAT RULE: When a user asks for a recipe, first provide 3 DISTINCT CANDIDATE OPTIONS in this exact format:\n'
 '### Options Found:\n'
 '1. **Option A: [Recipe Name]** (~[Time] mins | [Kcal] kcal) - [1-line description]\n'
 '2. **Option B: [Recipe Name]** (~[Time] mins | [Kcal] kcal) - [1-line description]\n'
 '3. **Option C: [Recipe Name]** (~[Time] mins | [Kcal] kcal) - [1-line description]\n\n'
 'Then follow with the full detailed recipe for Option A including USDA Nutrition Totals and Step-by-Step instructions.\n'
 f'{summary_block}'
 )

 llm = ChatOpenAI(
 model=settings.OPENROUTER_MODEL,
 openai_api_key=settings.OPENROUTER_API_KEY,
 openai_api_base='https://openrouter.ai/api/v1',
 temperature=0.2,
 max_tokens=1500,
 )

 if ALL_TOOLS:
 llm = llm.bind_tools(ALL_TOOLS)

 sys_msg = SystemMessage(content=sys_prompt)
 full_messages = [sys_msg] + messages
 response = llm.invoke(full_messages)

 return {'messages': [response]}

tools_execution_node = ToolNode(ALL_TOOLS)