from typing import TypedDict, Annotated, List, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ChefBotState(TypedDict):
    """
    LangGraph TypedDict State Schema.
    Tracks conversation message stream, dietary restrictions, and tool configuration.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    dietary_profile: str
    allow_web_search: bool
    thread_id: str
