import os
import json
from typing import cast
from langgraph.graph import MessagesState # type: ignore
from langchain_core.tools import tool # type: ignore
from langchain_core.runnables import RunnableConfig # type: ignore
from langchain_core.messages import AIMessage, ToolMessage # type: ignore

from mapboxgl.utils import create_color_stops, df_to_geojson # type: ignore
from mapboxgl.viz import CircleViz # type: ignore

# Import the AgentState from the state module
from travel.state import AgentState

# Getting the Mapbox token from environment variables
map_box_token = os.getenv('MAPBOX_ACCESS_TOKEN')

@tool
def map_trip(trip_id: str):
    """Map a trip by its ID."""
    return f"Mapping trip {trip_id}"

def trip_to_geojson(trip):
    features = []
    for place in trip.get("places", []):
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [place["longitude"], place["latitude"]],
            },
            "properties": {
                "id": place.get("id"),
                "name": place.get("name"),
                "address": place.get("address"),
                "rating": place.get("rating"),
                "description": place.get("description"),
            }
        }
        features.append(feature)
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    return geojson

def map_trip_node(state: AgentState, config: RunnableConfig):
    """ Map the selected trip ID """
    
    # Get the AI message from chat node
    ai_message = cast(AIMessage, state["messages"][-1])
    
    # Get the selected trip ID from the state
    selected_trip_id = state.get("selected_trip_id")
    
    # If no trip is selected, return an error message
    if not selected_trip_id:
        return {
            "messages": [AIMessage(content="No trip selected to map.")],
            "selected_trip_id": None
        }

    # Find the trip in the state
    selected_trip = next((trip for trip in state["trips"] if trip["id"] == selected_trip_id), None)
    
    # If no trip is found, return an error message
    if not selected_trip:
        return {
            "messages": [AIMessage(content="Selected trip not found.")],
            "selected_trip_id": None
        }

    # Convert the trip to GeoJSON format
    trip_geojson = trip_to_geojson(selected_trip)
    
    # Mapbox Configurations
    center = selected_trip.get("center_longitude"), selected_trip.get("center_latitude")
    zoom = selected_trip.get("zoom")
    style_url = 'mapbox://styles/mapbox/outdoors-v11'
    color_breaks = range(0, 6)
    color_stops = create_color_stops(color_breaks, colors='YlGnBu')

    # Create a Mapbox CircleViz object
    viz = CircleViz(style=style_url,
                    data=trip_geojson,
                    access_token=map_box_token,
                    height='400px',
                    width='1000px',
                    color_property = "rating",
                    color_stops = color_stops,
                    center = center,
                    zoom = zoom-1,
                    stroke_width = 1,
                    stroke_color = 'black',
                    radius=3,
                    below_layer = 'poi-label',
                )

    viz.show()
    
    # Save the map as an HTML file
    viz.create_html("trip_map.html")
    
    state["messages"].append(ToolMessage(
        tool_call_id=ai_message.tool_calls[0]["id"],
        content=f"Mapped the trip {selected_trip_id} successfully. You can view it at: {os.path.abspath('trip_map.html')}"
    ))
    
    return state