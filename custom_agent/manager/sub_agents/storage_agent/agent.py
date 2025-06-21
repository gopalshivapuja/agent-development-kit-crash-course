from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext

# Tools for persistent storage, adapted from 6-persistent-storage/memory_agent/agent.py
# These tools will use the session state provided by the ADK framework.

def store_data(key: str, value: any, tool_context: ToolContext) -> dict:
    """Stores data in the persistent session state.

    Args:
        key: The key under which to store the data.
        value: The data to store (can be any serializable type).
        tool_context: Context for accessing and updating session state.

    Returns:
        A confirmation message.
    """
    print(f"--- Tool: store_data called for key '{key}' ---")
    tool_context.state[key] = value
    return {
        "action": "store_data",
        "key": key,
        "status": "success",
        "message": f"Data stored successfully for key: {key}",
    }

def retrieve_data(key: str, tool_context: ToolContext) -> dict:
    """Retrieves data from the persistent session state.

    Args:
        key: The key of the data to retrieve.
        tool_context: Context for accessing session state.

    Returns:
        The retrieved data or a message if not found.
    """
    print(f"--- Tool: retrieve_data called for key '{key}' ---")
    value = tool_context.state.get(key)
    if value is not None:
        return {
            "action": "retrieve_data",
            "key": key,
            "value": value,
            "status": "success",
        }
    else:
        return {
            "action": "retrieve_data",
            "key": key,
            "status": "not_found",
            "message": f"No data found for key: {key}",
        }

def delete_data(key: str, tool_context: ToolContext) -> dict:
    """Deletes data from the persistent session state.

    Args:
        key: The key of the data to delete.
        tool_context: Context for accessing and updating session state.

    Returns:
        A confirmation message.
    """
    print(f"--- Tool: delete_data called for key '{key}' ---")
    if key in tool_context.state:
        del tool_context.state[key]
        return {
            "action": "delete_data",
            "key": key,
            "status": "success",
            "message": f"Data deleted successfully for key: {key}",
        }
    else:
        return {
            "action": "delete_data",
            "key": key,
            "status": "not_found",
            "message": f"No data found for key: {key} to delete.",
        }

storage_agent = Agent(
    name="storage_agent",
    model="gemini-2.0-flash", # Or your preferred model
    description="Agent that stores, retrieves, and deletes data using session state.",
    instruction="""
    You are an agent that can manage persistent data.
    Use the `store_data` tool to save information.
    Use the `retrieve_data` tool to get information.
    Use the `delete_data` tool to remove information.
    The data is stored per session and will persist across interactions within the same session.
    """,
    tools=[store_data, retrieve_data, delete_data],
)
