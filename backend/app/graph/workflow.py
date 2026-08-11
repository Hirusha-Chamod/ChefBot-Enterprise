import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tools_condition
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.graph.state import ChefBotState
from app.graph.nodes import chefbot_agent_node, tools_execution_node

def create_chefbot_graph():
    """
    Compiles the LangGraph StateGraph engine with Neon DB PostgreSQL / Memory Checkpointer.
    """
    workflow = StateGraph(ChefBotState)

    # 1. Add Nodes
    workflow.add_node("agent", chefbot_agent_node)
    workflow.add_node("tools", tools_execution_node)

    # 2. Set Entry Point
    workflow.set_entry_point("agent")

    # 3. Add Conditional Edges (Router)
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END
        }
    )

    # 4. Add Edge from Tools back to Agent
    workflow.add_edge("tools", "agent")

    # 5. Compile with Checkpointer (PostgresSaver if DATABASE_URL is set, else MemorySaver)
    db_url = settings.DATABASE_URL
    if db_url and "postgresql://" in db_url:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg_pool import ConnectionPool
            
            pool = ConnectionPool(conninfo=db_url, max_size=10, kwargs={"autocommit": True})
            checkpointer = PostgresSaver(pool)
            checkpointer.setup()  # Creates checkpointer schema in Neon DB if not exists
            print("🟢 Connected to Neon DB PostgreSQL Checkpointer!")
            return workflow.compile(checkpointer=checkpointer)
        except Exception as e:
            print(f"⚠️ Neon DB Connection Warning: {e}. Falling back to MemorySaver...")

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Singleton compiled LangGraph application
chefbot_app = create_chefbot_graph()
