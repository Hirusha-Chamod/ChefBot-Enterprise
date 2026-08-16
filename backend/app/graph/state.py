from typing import TypedDict, List, Annotated, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ChefBotState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    dietary_profile: str
    allow_web_search: bool
    thread_id: str
    servings: int
    user_id: Optional[str]


