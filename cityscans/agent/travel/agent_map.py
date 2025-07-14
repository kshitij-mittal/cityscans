"""
This is the main entry point for the AI.
It defines the workflow graph and the entry point for the agent.
"""

from typing import cast, List

from langchain_core.messages import AIMessage, ToolMessage, SystemMessage # type: ignore
from langgraph.graph import StateGraph, MessagesState, START, END # type: ignore
# from langgraph.checkpoint.memory import MemorySaver # type: ignore

from travel.state import AgentState
from travel.chat import chat_node
from travel.search import search_node
from travel.trips import perform_trips_node
from travel.map_trip import map_trip_node

def chat_router(state: AgentState):
    """Route after the chat node."""
    # Extract the messages from the state
    messages = state.get("messages", [])
    # If the message is present and last instance of message is also AI Message
    if messages and isinstance(messages[-1], AIMessage):
        
        # Get the latest message as AI Message
        ai_message = cast(AIMessage, messages[-1])
        
        # If the last AI message has tool calls we need to determine to route to the
        # trips_node or search_node based on the tool name.
        if ai_message.tool_calls:
            tool_name = ai_message.tool_calls[0]["name"]
            if tool_name in ["add_trips", "update_trips", "delete_trips", "select_trip"]:
                return "perform_trips_node"
            if tool_name in ["search_for_places"]:
                return "search_node"
            if tool_name in ["map_trip"]:
                return "map_trip_node"
            return "chat_node"
    
    # If the message is present and last instance of message is also Tool Message
    # We return to chat node
    if messages and isinstance(messages[-1], ToolMessage):
        return "chat_node"
    
    # If there is no message, we end the graph run
    return END

# Initiate a state graph
graphbuilder=StateGraph(AgentState)

# Add Nodes
graphbuilder.add_node("chat_node", chat_node)
graphbuilder.add_node("search_node", search_node)

# Trips
graphbuilder.add_node("perform_trips_node", perform_trips_node)

# Map Node
graphbuilder.add_node("map_trip_node", map_trip_node)

# Add Edges
graphbuilder.add_edge(START, "chat_node")
graphbuilder.add_conditional_edges("chat_node", chat_router, ["search_node",
                                                              "chat_node", 
                                                              "perform_trips_node",
                                                              "map_trip_node",
                                                              END])

graphbuilder.add_edge("search_node", "chat_node")
graphbuilder.add_edge("perform_trips_node", "chat_node")
graphbuilder.add_edge("map_trip_node", "chat_node")

# Compile the graph
graph = graphbuilder.compile(
        # checkpointer=MemorySaver(),
        # interrupt_after=["perform_trips_node"]
    )