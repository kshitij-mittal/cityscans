import os
import json
from typing import Literal, List, Optional, cast

from langgraph.graph import MessagesState # type: ignore
from langchain_core.tools import tool # type: ignore

from langchain_core.runnables import RunnableConfig # type: ignore
from langchain_core.messages import AIMessage, ToolMessage # type: ignore

# Import the AgentState from the state module
from travel.state import AgentState, Trip

@tool
def add_trips(trips: List[Trip]):
    """Add one or many trips to the list"""

def handle_add_trips(state: AgentState, args: dict,
                     tool_call_id=None) -> ToolMessage:
    # Get the trip to be added 
    trips = args.get("trips", [])

    # Extend trips in state
    state["trips"].extend(trips)
    return ToolMessage(
        tool_call_id=tool_call_id,
        content=f"Successfully added the trip(s)!"
        )

@tool
def delete_trips(trip_ids: List[str]):
    """Delete one or many trips. YOU MUST NOT CALL this tool multiple times in a row!"""

def handle_delete_trips(state: AgentState, args: dict,
                        tool_call_id=None) -> ToolMessage:
    trip_ids = args.get("trip_ids", [])
    
    # Clear selected_trip if it's being deleted
    if state.get("selected_trip_id") and state["selected_trip_id"] in trip_ids:
        state["selected_trip_id"] = None

    state["trips"] = [trip for trip in state["trips"] if trip["id"] not in trip_ids]
    return ToolMessage(
        tool_call_id=tool_call_id,
        content=f"Successfully deleted the trip(s)!"
        )

@tool
def update_trips(trips: List[Trip]):
    """Update one or many trips"""

def handle_update_trips(state: AgentState, args: dict,
                        tool_call_id=None) -> ToolMessage:
    trips = args.get("trips", [])
    for trip in trips:
        state["trips"] = [
            {**existing_trip, **trip} if existing_trip["id"] == trip["id"] else existing_trip
            for existing_trip in state["trips"]
        ]
    return ToolMessage(
        tool_call_id=tool_call_id,
        content=f"Successfully updated the trip(s)!"
        )
    
@tool
def select_trip(trip_id: str):
    """Select a trip"""
    return f"Selected trip {trip_id}"

def perform_trips_node(state: AgentState, config: RunnableConfig):
    """Execute trip operations"""
    
    # Extract the AI message from the state
    ai_message = cast(AIMessage, state["messages"][-1])

    # Initialize the trips list if it doesn't exist
    if not state.get("trips"):
        state["trips"] = []
        
    for tool_call in ai_message.tool_calls:
        action = tool_call["name"]
        args = tool_call.get("args", {})
        # Extract the tool call ID from the AI message
        tool_call_id = tool_call["id"]

        if action == "add_trips":
            message = handle_add_trips(state, args, tool_call_id)
            state["messages"].append(message)
        elif action == "delete_trips":
            message = handle_delete_trips(state, args, tool_call_id)
            state["messages"].append(message)
        elif action == "update_trips":
            message = handle_update_trips(state, args, tool_call_id)
            state["messages"].append(message)
        # Optionally handle unknown actions

    return state