from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

# Define sub-agent tools
from .sub_agents.search_agent.agent import search_agent
from .sub_agents.storage_agent.agent import storage_agent
from .sub_agents.llm_agent.agent import llm_agent
from .sub_agents.voice_agent.agent import voice_agent

# Define regular tools
# from .tools.tools import get_current_time # Example: replace with your tool


root_agent = Agent(
    name="manager_agent",
    model="gemini-2.0-flash", # Or your preferred model
    description="Manager agent for custom use case",
    instruction="""
    You are a manager agent responsible for coordinating sub-agents to achieve complex tasks.
    Delegate tasks to the appropriate sub-agent based on their capabilities:
    - search_agent: For finding information on the internet.
    - storage_agent: For saving and recalling information.
    - llm_agent: For generating text or interacting with a language model with a specific persona.
    - voice_agent: For tasks involving voice input or output.

    Clearly define the task for each sub-agent and synthesize their outputs to fulfill the user's request.
    """,
    # Add your sub-agents here
    sub_agents=[search_agent, storage_agent, llm_agent, voice_agent], # Placeholder
    # Add your tools here, if any, for the manager agent itself
    tools=[
        # Example: AgentTool(news_analyst),
        # Example: get_current_time,
    ],
)
