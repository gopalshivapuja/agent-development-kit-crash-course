from google.adk.agents import Agent

# This is a basic LLM agent. It doesn't have specific tools yet,
# as the "calling an LLM with my persona" is handled by the agent's
# instruction and model.
# You might add tools later if specific pre-processing/post-processing
# or structured output generation is needed.

llm_agent = Agent(
    name="llm_agent",
    model="gemini-2.0-flash", # Or your preferred model
    description="Agent that interacts with an LLM with a specific persona",
    instruction="""
    You are a helpful assistant with a [Specify Persona Here, e.g., witty, formal, expert in X].
    Respond to the user's query according to your persona.
    Your goal is to provide information, generate text, or complete tasks as requested.
    """,
    # No specific tools for now, relies on inherent LLM capabilities.
    # Tools could be added for specific structured outputs or external data fetching if needed.
    tools=[],
)
