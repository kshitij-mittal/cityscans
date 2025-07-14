import os
import json
from dotenv import load_dotenv # type: ignore
from typing import cast

# Import the AgentState from the state module
from travel.state import AgentState

# Import the ncecessary tools
from travel.search import search_for_places
from travel.trips import add_trips, delete_trips, update_trips, select_trip
from travel.map_trip import map_trip

# LangChain imports
from langgraph.graph import MessagesState           # type: ignore
from langchain_core.messages import (SystemMessage, # type: ignore
                                     AIMessage, 
                                     ToolMessage)   
from langchain_core.runnables import RunnableConfig # type: ignore

# OpenAI imports
from langchain_openai import ChatOpenAI # type: ignore

# Load environment variables from .env file
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key is None:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

# Initialize the OpenAI chat model
llm=ChatOpenAI()

# Define the tools that the chat node can call
tools = [search_for_places, 
         add_trips, delete_trips, update_trips,
         select_trip,
         map_trip
         ]

# Chat Node
def chat_node(state: AgentState,              # Graph State 
              config: RunnableConfig):        # Graph Memory
    """Handle chat operations"""
    llm_with_tools = llm
    llm_with_tools = llm.bind_tools(
        [
            *tools,
        ],
        parallel_tool_calls=False,
    )

    system_message = f"""
    You are an agent that plans trips and helps the user with planning and managing their trips.
    If the user did not specify a location, you should ask them for a location.
    
    Plan the trips for the user, take their preferences into account if specified, but if they did not
    specify any preferences, call the search_for_places tool to find places of interest, restaurants, and activities.
    
    Unless the users prompt specifies otherwise, only use the first 3 results from the search_for_places tool relevant
    to the trip.
    
    When you add or edit a trip, you don't need to summarize what you added. Just give a high level summary of the trip
    and why you planned it that way.
    
    If the user asks to add it to the same trip, then you should update the trip rather than add a new one.
    
    When you create or update a trip, you should very importantly set it as the selected trip.
    If you delete a trip, try to select another trip.

    Ask the user if they want to finalize the trip after you have planned it. If they ask to select/finalize the trip, then run the select_trip tool with the trip ID.
    
    Once the user has finalized the trip, ask if they want to make a map for it.
    
    If an operation is cancelled by the user, DO NOT try to perform the operation again. Just ask what the user would like to do now
    instead.

    Current trips: {json.dumps(state.get('trips', []))}
    """

    # calling ainvoke instead of invoke is essential to get streaming to work properly on tool calls.
    
    # Getting the llm output
    response = llm_with_tools.invoke(
        [
            SystemMessage(content=system_message),
            *state["messages"]
        ],
        config=config,
    )

    # Casting Chat Node Output to AIMessage
    ai_message = cast(AIMessage, response)

    # Check if the AI message contains tool calls
    if ai_message.tool_calls:
        # Check if the first tool call is "select_trip"
        if ai_message.tool_calls[0]["name"] == "select_trip":
            # Extract the trip ID from the tool call arguments
            return {
                "selected_trip_id": ai_message.tool_calls[0]["args"].get("trip_id", ""),
                # Update the state with the selected trip ID
                "messages": [ai_message, ToolMessage(
                    tool_call_id=ai_message.tool_calls[0]["id"],
                    content="Trip selected."
                )]
            }

    # Final Output of the chat node
    return {
        "messages": [response],
        "selected_trip_id": state.get("selected_trip_id", None),
        "trips": state.get("trips", [])
    }