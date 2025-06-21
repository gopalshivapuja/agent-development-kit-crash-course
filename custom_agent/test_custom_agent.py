import unittest
import uuid
import asyncio # Import asyncio for async tests
from unittest.mock import patch, MagicMock

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService # SessionDatastore removed
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.genai import types as genai_types

# Import the manager agent (root_agent)
from custom_agent.manager.agent import root_agent as manager_agent
# Import sub-agents to potentially mock their direct tool calls if necessary, or their LLM calls
from custom_agent.manager.sub_agents.storage_agent.agent import storage_agent
from custom_agent.manager.sub_agents.search_agent.agent import search_agent
from custom_agent.manager.sub_agents.llm_agent.agent import llm_agent
from custom_agent.manager.sub_agents.voice_agent.agent import voice_agent


# The custom TestInMemorySessionDatastore class is removed as InMemorySessionService should be sufficient.

class TestCustomAgent(unittest.TestCase):
    def setUp(self):
        self.app_name = "custom_agent_test"
        self.user_id = "test_user"
        self.session_id = str(uuid.uuid4())

        # Use InMemorySessionService directly
        self.session_service = InMemorySessionService()
        self.artifact_service = InMemoryArtifactService()
        self.memory_service = InMemoryMemoryService()

        # Create an initial session
        self.session_service.create_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=self.session_id,
            state={},
        )

        self.runner = Runner(
            agent=manager_agent,
            session_service=self.session_service,
            artifact_service=self.artifact_service,
            memory_service=self.memory_service,
            app_name=self.app_name,
        )

    def _mock_llm_call(self, tool_to_call=None, tool_input=None, final_text_response="LLM final response."):
        """
        Mocks the behavior of the LLM.
        If tool_to_call is specified, it simulates the LLM deciding to call that tool.
        Otherwise, it simulates the LLM providing a direct text response.
        """
        mock_event_content = MagicMock()
        if tool_to_call:
            # Simulate LLM wanting to call a tool
            function_call_part = genai_types.Part(
                function_call=genai_types.FunctionCall(name=tool_to_call, args=tool_input or {})
            )
            mock_event_content.parts = [function_call_part]
        else:
            # Simulate LLM giving a direct text response
            text_part = genai_types.Part(text=final_text_response)
            mock_event_content.parts = [text_part]

        # This structure tries to mimic what the agent's LLM interaction might yield.
        # The actual structure might depend on how `generate_content_async` is processed by the ADK.
        # We are mocking the *output* that the agent's `_call_llm_async` (or similar internal method) would return
        # or the events it would generate.
        # For simplicity, we'll mock `generate_content_async` on the `GenerativeModel` instance used by agents.

        mock_llm_response = MagicMock()
        # This part is tricky: what exactly does generate_content_async return that the Runner processes?
        # It's an AsyncIterable[GenerateContentResponse].
        # Let's mock the response object that would be iterated.
        mock_generate_content_response = MagicMock(spec=genai_types.GenerateContentResponse)

        # Simplification: Assume a single candidate and the content is directly usable.
        # In reality, GenerateContentResponse has candidates, which then have content.
        mock_candidate = MagicMock()
        mock_candidate.content = mock_event_content
        mock_generate_content_response.candidates = [mock_candidate]

        # If mocking generate_content_async, it should be an async generator
        async def async_generator():
            yield mock_generate_content_response

        return async_generator()


    @patch("google.generativeai.GenerativeModel.generate_content_async")
    async def test_manager_delegates_to_search_agent_async(self, mock_gen_content):
        # 1. Manager decides to call search_agent
        mock_gen_content.side_effect = [
            self._mock_llm_call(tool_to_call=search_agent.name, tool_input={"query": "weather"}),
            # 2. search_agent itself (an LlmAgent) decides to call GoogleSearchTool
            self._mock_llm_call(tool_to_call="google_search", tool_input={"query": "weather"}),
            # 3. Manager receives result from search_agent (which got it from GoogleSearchTool) and formulates final response
            self._mock_llm_call(final_text_response="Search results: Sunny via mock.")
        ]

        query = "What's the weather like?"
        new_message = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])

        final_response_text = None
        # Patch the actual tool used by search_agent
        with patch.object(search_agent.tools[0], '__call__', return_value="Mocked Google Search Result: Sunny") as mock_google_tool:
            async for event in self.runner.run_async(
                user_id=self.user_id, session_id=self.session_id, new_message=new_message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text

        self.assertIn("Search results: Sunny via mock.", final_response_text)
        self.assertEqual(mock_gen_content.call_count, 3)
        # mock_google_tool.assert_called_once_with(query="weather") # This specific check might be too brittle

    @patch("google.generativeai.GenerativeModel.generate_content_async")
    async def test_manager_delegates_to_storage_agent_store_and_retrieve_async(self, mock_gen_content):
        # --- Store Operation ---
        # 1. Manager decides to call storage_agent for storing
        mock_gen_content.side_effect = [
            self._mock_llm_call(tool_to_call=storage_agent.name, tool_input={"action": "store", "key": "city", "value": "Paris"}),
            # 2. storage_agent decides to call its 'store_data' tool
            self._mock_llm_call(tool_to_call="store_data", tool_input={"key": "city", "value": "Paris"}),
            # 3. Manager processes confirmation from storage_agent
            self._mock_llm_call(final_text_response="OK, I've stored that Paris is the city.")
        ]

        query1 = "Remember the city is Paris."
        new_message1 = genai_types.Content(role="user", parts=[genai_types.Part(text=query1)])

        response_text1 = None
        async for event in self.runner.run_async(user_id=self.user_id, session_id=self.session_id, new_message=new_message1):
            if event.is_final_response() and event.content and event.content.parts:
                response_text1 = event.content.parts[0].text

        self.assertIn("OK, I've stored that Paris is the city.", response_text1)
        self.assertEqual(mock_gen_content.call_count, 3)

        session_data = self.session_service.get_session(self.app_name, self.user_id, self.session_id)
        self.assertEqual(session_data.state.get("city"), "Paris")

        # --- Retrieve Operation ---
        mock_gen_content.reset_mock()
        # 1. Manager decides to call storage_agent for retrieving
        mock_gen_content.side_effect = [
             self._mock_llm_call(tool_to_call=storage_agent.name, tool_input={"action": "retrieve", "key": "city"}),
            # 2. storage_agent decides to call its 'retrieve_data' tool
            self._mock_llm_call(tool_to_call="retrieve_data", tool_input={"key": "city"}),
            # 3. Manager processes retrieved data from storage_agent
            self._mock_llm_call(final_text_response="The city I remember is Paris.")
        ]

        query2 = "What city did I tell you about?"
        new_message2 = genai_types.Content(role="user", parts=[genai_types.Part(text=query2)])

        response_text2 = None
        async for event in self.runner.run_async(user_id=self.user_id, session_id=self.session_id, new_message=new_message2):
            if event.is_final_response() and event.content and event.content.parts:
                response_text2 = event.content.parts[0].text

        self.assertIn("The city I remember is Paris.", response_text2)
        self.assertEqual(mock_gen_content.call_count, 3)

    @patch("google.generativeai.GenerativeModel.generate_content_async")
    async def test_manager_delegates_to_llm_agent_async(self, mock_gen_content):
        # 1. Manager decides to call llm_agent
        mock_gen_content.side_effect = [
            self._mock_llm_call(tool_to_call=llm_agent.name, tool_input={"query": "Tell me a joke"}),
            # 2. llm_agent (being an LlmAgent with no tools) directly responds using its LLM.
            #    The instruction of llm_agent ("Specify Persona Here...") will be part of the prompt.
            self._mock_llm_call(final_text_response="Why don't scientists trust atoms? Because they make up everything!"),
            # 3. Manager processes/relays the response from llm_agent
            self._mock_llm_call(final_text_response="LLM sub-agent says: Why don't scientists trust atoms? Because they make up everything!")
        ]

        query = "Tell me a joke."
        new_message = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])

        final_response_text = None
        async for event in self.runner.run_async(user_id=self.user_id, session_id=self.session_id, new_message=new_message):
            if event.is_final_response() and event.content and event.content.parts:
                final_response_text = event.content.parts[0].text

        self.assertIn("Why don't scientists trust atoms?", final_response_text)
        self.assertEqual(mock_gen_content.call_count, 3)
        # Check that llm_agent's specific instruction was part of the prompt in the second LLM call
        # This requires inspecting the arguments passed to mock_gen_content.
        # The call_args_list stores tuples of (args, kwargs). We need the `messages` or `contents` part.
        # Assuming system_instruction is used for the agent's instruction.
        llm_agent_call_args = mock_gen_content.call_args_list[1]
        # The exact structure of how system_instruction is passed might vary.
        # It could be in `llm_request.system_instruction` or part of `llm_request.contents`.
        # For this mock, we need to ensure the call to the LLM for the llm_agent included its persona.
        # This is a bit of an indirect check.
        # A more robust check would be if the LlmAgent class allows inspecting the prompt it constructs.
        # For now, let's assume the instruction is present in the system_instruction part of the call.
        passed_system_instruction_to_llm_agent_llm = str(llm_agent_call_args[0][0].system_instruction) # Example path
        self.assertIn("Specify Persona Here", passed_system_instruction_to_llm_agent_llm)


    @patch("google.generativeai.GenerativeModel.generate_content_async")
    async def test_manager_delegates_to_voice_agent_tts_async(self, mock_gen_content):
        # 1. Manager decides to call voice_agent for TTS
        mock_gen_content.side_effect = [
            self._mock_llm_call(tool_to_call=voice_agent.name, tool_input={"action": "speak", "text": "Hello world"}),
            # 2. voice_agent decides to use its TextToSpeechTool
            self._mock_llm_call(tool_to_call="text_to_speech", tool_input={"text_to_speak": "Hello world"}),
            # 3. Manager processes (mocked) confirmation from voice_agent
            self._mock_llm_call(final_text_response="I've sent 'Hello world' to be spoken (mocked).")
        ]

        # Patch the actual TextToSpeechTool used by voice_agent
        # voice_agent.tools is a list, TextToSpeechTool is the first one.
        with patch.object(voice_agent.tools[0], '__call__', return_value="Mocked TTS: Speech generated for: Hello world") as mock_tts_actual_tool:
            query = "Say 'Hello world'"
            new_message = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])

            final_response_text = None
            async for event in self.runner.run_async(user_id=self.user_id, session_id=self.session_id, new_message=new_message):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text

            self.assertIn("I've sent 'Hello world' to be spoken (mocked).", final_response_text)
            self.assertEqual(mock_gen_content.call_count, 3)
            # Check that the *actual tool function* on voice_agent was called
            # mock_tts_actual_tool.assert_called_once_with(text_to_speak="Hello world") # This is for the tool's __call__

# This allows running tests with `python -m unittest test_file.py`
if __name__ == "__main__":
    # For running async tests with unittest
    asyncio.run(unittest.main())
