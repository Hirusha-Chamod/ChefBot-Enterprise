from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tools_condition
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import ChefBotState
from app.graph.nodes import chefbot_agent_node, tools_execution_node

def create_chefbot_graph():
    """
    Compiles the LangGraph StateGraph engine with session memory checkpointer.
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

    # 5. Compile with MemorySaver Checkpointer
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Singleton compiled LangGraph application
chefbot_app = create_chefbot_graph()
