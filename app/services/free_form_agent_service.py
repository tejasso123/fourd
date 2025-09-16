import json
import asyncio
import re
from typing import Optional
from phi.agent import Agent
from phi.memory import AgentMemory
from phi.memory.agent import MemoryRetrieval
from phi.model.openai import OpenAIChat
from phi.knowledge.agent import AgentKnowledge
from phi.vectordb.pgvector import SearchType
from app.core.context import loggedin_user_var
from app.services.drive_service import fetch_drive_file_content
from app.core import settings
from app.services.storage_cache import get_cached_storage, get_cached_memory_db, get_cached_custom_vector_db
from app.utils import redis_client
from app.core.exceptions import InternalServerErrorException

# -------------------- Environment Variables --------------------
OPENAI_API_KEY = settings.OPENAI_API_KEY
SYNC_DB_STR = settings.SYNC_DB_STR
FOLDER_NAME = "DoshaQuiz"
OPENAI_MODEL = settings.OPENAI_MODEL
NUM_HISTORY_RESPONSES = settings.NUM_HISTORY_RESPONSES
VECTOR_SEARCH_LIMIT = settings.VECTOR_SEARCH_LIMIT
OPENAI_TEMP = 0.5
TOP_P = 0.9
IS_PROD = settings.ENV == "prod"
CACHED_FILES = {
    "free_form_commands_content": "free_form_commands.md"
}


# -------------------- Async Load Instructions, Commands and SOPs --------------------
async def load_instructions_and_commands(drive_service):
    """Load instructions and commands from Google Drive or Redis Cache asynchronously."""

    content = {}
    for key, file_name in CACHED_FILES.items():
        cached_content = await redis_client.get_value_async(key)
        if cached_content is None:
            cached_content = await fetch_drive_file_content(drive_service, file_name,
                                                            f"{FOLDER_NAME}")
            await redis_client.set_value_async(key, cached_content)
        content[key] = cached_content

    return content


# -------------------- Initialize AI Agent --------------------

async def get_agent(session_id: Optional[str], agent_id: Optional[str]) -> Agent:
    """Initialize the AI Agent asynchronously with knowledge and memory."""

    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)
    dim3_value = current_user.dim3
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.vector, VECTOR_SEARCH_LIMIT)
    storage = get_cached_storage(dim3_value)

    return Agent(
        name="ayurvedic_content_generator ",
        description="Expert Ayurvedic practitioner that generates professional HTML-formatted content for any Ayurvedic question or topic, from simple answers to comprehensive guides, optimized for React.js rendering.",
        task="Create accurate, culturally-sensitive Ayurvedic content in professional HTML format with inline CSS styling, adapting response length and structure based on user queries while maintaining educational value and safety considerations.",
        prevent_hallucinations=True,
        knowledge=AgentKnowledge(vector_db=vector_db),
        storage=storage,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        add_context=False,
        markdown=True,
        add_chat_history_to_messages=False,
        read_chat_history=False,
        num_history_responses=0,
        debug_mode=not IS_PROD,
        prevent_prompt_leakage=True,
        search_knowledge=False,
        structured_outputs=True,
        parse_response=True
    )


# -------------------- Shared Prep Logic --------------------

async def prepare_agent_and_prompt(drive_service, **kwargs):
    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)

    agent = await get_agent(kwargs.get("session_id"), kwargs.get("agent_id"))

    agent.model = OpenAIChat(
        id="gpt-4o-mini",
        model="gpt-4o-mini",
        max_completion_tokens=5000,
        temperature=OPENAI_TEMP,
        api_key=OPENAI_API_KEY,
        top_p=TOP_P,
        user=user_id,
        session_id=kwargs.get("session_id"),
        response_format={"type": "json_object"}

    )

    cached_content = await load_instructions_and_commands(drive_service)

    format_args = {
        "further_details": kwargs.get("further_details", ""),
        "language": kwargs.get("language", ""),
        "location_focus": kwargs.get("location_focus", ""),
        "role": kwargs.get("role", ""),
        "goal": kwargs.get("goal", ""),
        "constraints": kwargs.get("constraints", "")
    }
    formatted_prompt = cached_content[f"free_form_commands_content"].format(**format_args)

    return agent, formatted_prompt


# -------------------- AI Query Execution --------------------

async def ask_fouray_free_form_stream(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        agent, prompt = await prepare_agent_and_prompt(drive_service, **kwargs)
        page_image = kwargs.get("image", "")

        async for chunk in execute_search_and_generate_response_stream(knowledge_context="", combined_prompt=prompt,
                                                                       agent=agent, page_image=page_image):
            yield chunk

    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


# -------------------- Utility Functions --------------------

def format_prompt(knowledge_context, combined_prompt):
    prompt = ""
    if knowledge_context:
        prompt += f"\n\n## Knowledge Base:\n{knowledge_context}"
    if combined_prompt:
        prompt += f"\n\n## Query:\n{combined_prompt}"
    return prompt


async def execute_search_and_generate_response_stream(knowledge_context: Optional[str] = None,
                                                      combined_prompt: Optional[str] = None, agent: Agent = None,
                                                      page_image: str = ""):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """

    agent.search_knowledge = False
    prompt = format_prompt(knowledge_context, combined_prompt)
    images = [page_image]

    try:

        del knowledge_context
        del combined_prompt
        import gc
        gc.collect()
        print("Memory clean up before streaming")

        # This will return an iterator (not async)
        for chunk in agent.run(prompt, stream=True, images=images if images else None):
            value = getattr(chunk, "content", chunk)

            try:
                # First try to parse it as JSON
                parsed = json.loads(value) if isinstance(value, str) else value
            except json.JSONDecodeError:
                parsed = value  # fallback if it's not valid JSON

            if isinstance(parsed, dict) and "response" in parsed:
                for item in parsed["response"]:
                    yield json.dumps(item)
            elif isinstance(parsed, list):
                for item in parsed:
                    yield json.dumps(item)
            else:
                yield str(parsed)

            await asyncio.sleep(0)
        del prompt
        gc.collect()
        print("Memory cleaned up")
    except Exception as e:
        raise InternalServerErrorException(f"Streaming error: {str(e)}")
