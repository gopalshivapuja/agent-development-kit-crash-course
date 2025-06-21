from google.adk.agents import Agent
from google.adk.tools.google_search_tool import GoogleSearchTool

search_agent = Agent(
    name="search_agent",
    model="gemini-2.0-flash", # Or your preferred model
    description="Agent that searches Google",
    instruction="You are an agent that searches Google for information. Use the GoogleSearchTool to find relevant information based on the user's query.",
    tools=[GoogleSearchTool],
)
