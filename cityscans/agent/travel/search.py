import os
import json
from typing import cast
from langgraph.graph import MessagesState # type: ignore
from langchain_core.tools import tool # type: ignore
from langchain_core.runnables import RunnableConfig # type: ignore
from langchain_core.messages import AIMessage, ToolMessage # type: ignore

import googlemaps # type: ignore


# Import the AgentState from the state module
from travel.state import AgentState

gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

@tool
def search_for_places(queries: list[str]) -> list[dict]:
    """Search for places based on a query, returns a list of places including their name, address, and coordinates."""

def search_node(state: AgentState, config: RunnableConfig):
    """
    The search node is responsible for searching for the places.
    """
    # Get the AI message from chat node
    ai_message = cast(AIMessage, state["messages"][-1])

    # Get the search progress from graph state
    state["search_progress"] = state.get("search_progress", [])
    
    # Get the queries from the AI message
    queries = ai_message.tool_calls[0]["args"]["queries"]

    # Update search progress in state
    for query in queries:
        state["search_progress"].append({
            "query": query,
            "results": [],
            "done": False
        })


    # Initiate the places dictionary
    places = []
    
    # For each query in the queries, search for the places
    # and add them to the places dictionary
    for i, query in enumerate(queries):
        
        # Get the response dictionary from the Google Maps API
        response = gmaps.places(query)
        # Parse the response dictionary
        for result in response.get("results", []):
            # Extract place information from gmaps response
            place = {
                "id": result.get("place_id", f"{result.get('name', '')}-{i}"),
                "name": result.get("name", ""),
                "address": result.get("formatted_address", ""),
                "latitude": result.get("geometry", {}).get("location", {}).get("lat", 0),
                "longitude": result.get("geometry", {}).get("location", {}).get("lng", 0),
                "rating": result.get("rating", 0),
            }
            places.append(place)
        # Update the search progress in state
        state["search_progress"][i]["done"] = True
        # await copilotkit_emit_state(config, state)

    # Re-initiating the search progress
    state["search_progress"] = []

    # Adding tool message to the state
    state["messages"].append(ToolMessage(
        tool_call_id=ai_message.tool_calls[0]["id"],
        content=f"Added the following search results: {json.dumps(places)}"
    ))

    return state