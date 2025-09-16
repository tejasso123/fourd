import json
import asyncio
from typing import Optional
from phi.agent import Agent
from phi.memory import AgentMemory
from phi.memory.agent import MemoryRetrieval
from phi.model.openai import OpenAIChat
from phi.knowledge.agent import AgentKnowledge
from phi.vectordb.pgvector import SearchType

from app.core.context import loggedin_user_var
from app.services.ProductAgent import ProductDescriptionAgent
from app.services.drive_service import fetch_drive_file_content
from app.core import settings
from app.services.storage_cache import get_cached_custom_vector_db, get_cached_storage, get_cached_memory_db
from app.utils import redis_client
from app.core.exceptions import InternalServerErrorException

# -------------------- Environment Variables --------------------
OPENAI_API_KEY = settings.OPENAI_API_KEY
SYNC_DB_STR = settings.SYNC_DB_STR
FOLDER_NAME = "Translate"
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TEMP = 0.1
TOP_P = 0.9
IS_PROD = settings.ENV == "prod"
CACHED_FILES = {
    "translate_content_commands_content": "translate_commands_content.md"
}


# -------------------- Async Load Instructions & Commands --------------------
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

async def get_agent(session_id: Optional[str], agent_id: Optional[str]) -> ProductDescriptionAgent:
    """Initialize the AI Agent asynchronously with knowledge and memory."""

    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)
    dim3_value = current_user.dim3
    storage = get_cached_storage(dim3_value)

    return ProductDescriptionAgent(
        name="multilingual_content_translator",
        description="Translates JSON-structured content across languages while maintaining data integrity, applying regional compliance, and preserving exact structural formatting.",
        task="Convert JSON data from source language to target language with regional localization, ensuring zero structural changes while applying cultural and regulatory adaptations.",
        prevent_hallucinations=True,
        storage=storage,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        markdown=True,
        debug_mode=not IS_PROD,
        prevent_prompt_leakage=True,
        parse_response=True,
        structured_outputs=True,
    )


# -------------------- Shared Prep Logic --------------------

async def prepare_agent_and_prompt(drive_service, **kwargs):
    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)

    agent = await get_agent(kwargs.get("session_id"), kwargs.get("agent_id"))

    agent.model = OpenAIChat(
        id=OPENAI_MODEL,
        model=OPENAI_MODEL,
        max_completion_tokens=10000,
        temperature=OPENAI_TEMP,
        api_key=OPENAI_API_KEY,
        top_p=TOP_P,
        user=user_id,
        session_id=kwargs.get("session_id"),
        response_format={"type": "json_object"},
    )

    cached_content = await load_instructions_and_commands(drive_service)

    format_args = {
        "json_data": kwargs.get("json_data", ""),
        "source_language": kwargs.get("source_language", ""),
        "target_language": kwargs.get("target_language", ""),
        "target_region": kwargs.get("target_region", ""),
        "tone": kwargs.get("tone", "")
    }
    formatted_prompt = cached_content[f"translate_content_commands_content"].format(**format_args)

    return agent, formatted_prompt


# -------------------- AI Query Execution --------------------

async def translate_content_stream(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        agent, prompt = await prepare_agent_and_prompt(drive_service, **kwargs)

        async for chunk in execute_search_and_generate_response_stream(combined_prompt=prompt,
                                                                       agent=agent):
            yield chunk

    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


def format_prompt(combined_prompt):
    prompt = ""
    if combined_prompt:
        prompt += f"\n\n## Query:\n{combined_prompt}"

    return prompt


async def execute_search_and_generate_response_stream(combined_prompt: Optional[str] = None,
                                                      agent: Agent = None):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """

    agent.search_knowledge = False
    prompt = format_prompt(combined_prompt)

    try:

        del combined_prompt
        import gc
        gc.collect()
        print("Memory clean up before streaming")

        # This will return an iterator (not async)
        for chunk in agent.run(prompt, stream=True):
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
