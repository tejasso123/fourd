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
    "product_dosha_quiz_commands_content": "dosha_quiz_commands.md"
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
        name="ayurvedic_dosha_analyzer ",
        description="Explains it analyzes dosha questionnaire data and creates personalized health reports in simple language.",
        task="Specifies creating concise, user-friendly Ayurvedic constitution reports with practical recommendations.",
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
        id="gpt-4o",
        model="gpt-4o",
        max_completion_tokens=2000,
        temperature=OPENAI_TEMP,
        api_key=OPENAI_API_KEY,
        top_p=TOP_P,
        user=user_id,
        session_id=kwargs.get("session_id"),
        response_format={"type": "json_object"}

    )

    cached_content = await load_instructions_and_commands(drive_service)

    format_args = {
        "quiz_json": kwargs.get("quiz_json", "")
    }
    formatted_prompt = cached_content[f"product_dosha_quiz_commands_content"].format(**format_args)

    return agent, formatted_prompt


# -------------------- AI Query Execution --------------------

async def ask_fouray_dosha_quiz_stream(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        agent, prompt = await prepare_agent_and_prompt(drive_service, **kwargs)

        async for chunk in execute_search_and_generate_response_stream(knowledge_context="", combined_prompt=prompt,
                                                                       agent=agent):
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
                                                      combined_prompt: Optional[str] = None, agent: Agent = None):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """

    agent.search_knowledge = False
    prompt = format_prompt(knowledge_context, combined_prompt)

    try:
        del knowledge_context
        del combined_prompt
        import gc
        gc.collect()
        print("Memory clean up before streaming")

        buffer = ""
        inside_array = False
        brace_depth = 0
        object_buffer = ""
        # This will return an iterator (not async)
        for chunk in agent.run(prompt, stream=True):

            value = getattr(chunk, "content", chunk)
            if not isinstance(value, str):
                continue

            buffer += value

            # Wait until we find the start of the "response": [ section
            if not inside_array and "[" in buffer:
                inside_array = True
                buffer = buffer.split("[", 1)[1]
                continue

            if inside_array:
                for char in value:
                    if char == "{":
                        if brace_depth == 0:
                            object_buffer = ""
                        brace_depth += 1
                        object_buffer += char
                    elif char == "}":
                        brace_depth -= 1
                        object_buffer += char
                        if brace_depth == 0:
                            try:
                                obj = json.loads(object_buffer)
                                yield f"data: {json.dumps(obj)}\n\n"
                                await asyncio.sleep(0.01)
                            except json.JSONDecodeError:
                                # malformed or partial
                                pass
                            object_buffer = ""
                    elif brace_depth > 0:
                        object_buffer += char

            await asyncio.sleep(0)
        del prompt
        del buffer
        del inside_array
        del brace_depth
        del object_buffer
        gc.collect()
        print("Memory cleaned up")

    except Exception as e:
        raise InternalServerErrorException(f"Streaming error: {str(e)}")
