import json
import asyncio
import re
from typing import Optional
from phi.agent import Agent
from phi.memory import AgentMemory
from phi.memory.agent import MemoryRetrieval
# from phi.memory import AgentMemory
# from phi.memory.agent import MemoryRetrieval
# from phi.memory.db.postgres import PgMemoryDb
from phi.model.openai import OpenAIChat
from phi.knowledge.agent import AgentKnowledge
# from phi.reranker.cohere import CohereReranker
# from phi.storage.agent.postgres import PgAgentStorage
from phi.vectordb.pgvector import SearchType
from app.core.context import loggedin_user_var
from app.services.LegalGVAgent import LegalGVAgent
from app.services.drive_service import fetch_drive_file_content
from app.core import settings
from app.services.storage_cache import get_cached_storage, get_cached_custom_vector_db, get_cached_memory_db
from app.utils import redis_client, AgentManager
from app.core.exceptions import InternalServerErrorException

# import time

# -------------------- Environment Variables --------------------
OPENAI_API_KEY = settings.OPENAI_API_KEY
SYNC_DB_STR = settings.SYNC_DB_STR
INSTRUCTION_COMMAND_FOLDER_NAME = "GlobeviewAI"
OPENAI_MODEL = 'gpt-4o'  # settings.OPENAI_MODEL
OPENAI_LOWER_MODEL = settings.OPENAI_LOWER_MODEL
OPENAI_TEMP = 0
TOP_P = 0.9
NUM_HISTORY_RESPONSES = settings.NUM_HISTORY_RESPONSES
VECTOR_SEARCH_LIMIT = 45
IS_PROD = settings.ENV == "prod"


# -------------------- Async Load Instructions & Commands --------------------

async def load_instructions_and_commands(drive_service, niche: str):
    """Load instructions and commands from Google Drive or Redis Cache asynchronously."""

    key_files = {
        "gv_instructions_content": settings.INSTRUCTIONS_FILE_NAME,
        "gv_commands_content": settings.COMMANDS_FILE_NAME,
        "gv_agent_config_key": settings.AGENT_CONFIG_FILE_NAME,
        f"gv_agent_{niche}_context_key": settings.AGENT_CONTEXT_FILE_NAME.format(niche=niche),
        f"gv_agent_{niche}_additional_context_key": settings.AGENT_ADDITIONAL_CONTEXT_FILE_NAME.format(niche=niche),
    }

    content = {}
    for key, file_name in key_files.items():
        cached_content = await redis_client.get_value_async(key)
        if cached_content is None:
            cached_content = await fetch_drive_file_content(drive_service, file_name, INSTRUCTION_COMMAND_FOLDER_NAME)
            await redis_client.set_value_async(key, cached_content)
        content[key] = cached_content

    return content


# -------------------- Initialize AI Agent --------------------

async def get_agent(session_id: Optional[str], agent_id: Optional[str]) -> LegalGVAgent:
    """Initialize the AI Agent asynchronously with knowledge and memory."""

    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)
    dim3_value = current_user.dim3
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.vector, VECTOR_SEARCH_LIMIT)
    storage = get_cached_storage(dim3_value)
    memory_db = get_cached_memory_db(dim3_value)

    memory = AgentMemory(
        messages=[],
        db=memory_db,
        user_id=user_id,
        retrieval=MemoryRetrieval.last_n,
        create_user_memories=True,
        update_user_memories_after_run=True,
        update_system_message_on_change=True,
        updating_memory=True,
        num_memories=5,
    )

    return LegalGVAgent(
        name="far_function_mapper",
        description="AI agent designed to assist with legal and financial document analysis, function mapping, and knowledge extraction.",
        task="Analyze provided documents and generate structured insights for legal, compliance, or regulatory use cases.",
        prevent_hallucinations=True,
        knowledge=AgentKnowledge(vector_db=vector_db),
        memory=memory,
        storage=storage,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        add_context=True,
        search_knowledge=False,
        markdown=True,
        add_chat_history_to_messages=False,
        read_chat_history=False,
        update_knowledge=True,
        num_history_responses=0,
        debug_mode=not IS_PROD,
        # reasoning=True,
        prevent_prompt_leakage=True,
        parse_response=True,
        structured_outputs=True
    )


# -------------------- Shared Prep Logic --------------------

async def prepare_agent_and_prompt(drive_service, **kwargs):
    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)

    agent = await get_agent(kwargs.get("session_id"), kwargs.get("agent_id"))
    agent.model = OpenAIChat(
        id=OPENAI_MODEL,
        model=OPENAI_MODEL,
        max_completion_tokens=4000,
        temperature=OPENAI_TEMP,
        api_key=OPENAI_API_KEY,
        top_p=TOP_P,
        user=user_id,
        session_id=kwargs.get("session_id"),
        response_format={"type": "json_object"},
    )

    content = await load_instructions_and_commands(drive_service, kwargs.get("niche", ""))

    format_args = {
        "parent_entity": kwargs.get("parent_entity", ""),
        "associate_enterprise": kwargs.get("associate_enterprise", "")
    }

    agent.instructions = [content["gv_agent_config_key"].format(**format_args)]
    formatted_prompt = content["gv_commands_content"].format(**format_args)
    user_prompt = ""
    if not kwargs.get("user_input"):
        agent.guidelines = content[f"gv_agent_{kwargs.get("niche", "")}_additional_context_key"]
        agent.context = json.loads(content[f"gv_agent_{kwargs.get("niche", "")}_context_key"])
        agent.system_prompt = content["gv_agent_config_key"].format(**format_args)
        # agent.expected_output = settings.LEGAL_GV_EXPECTED_OUTPUT
    else:
        # formatted_prompt = user_input + "\nIf needed keep this user input in knowledgebase/memory while answering the future questions"
        agent.update_knowledge = True
        # user_prompt = f"{'User Input: ' + section_name if section_name else ''}{user_input}\n\nIf needed keep this user input in knowledgebase or memory while answering the future questions"
        user_prompt = f"{'User Input: ' + kwargs.get("section_name") if kwargs.get("section_name") else ''}{'-- ' + kwargs.get("user_input")}"
        # agent.expected_output = settings.LEGAL_GV_USER_PROMPT_EXPECTED_OUTPUT

    agent.read_chat_history = True
    agent.add_chat_history_to_messages = True
    agent.num_history_responses = NUM_HISTORY_RESPONSES

    return agent, formatted_prompt, user_prompt


async def ask_fouray_legal_gv_stream(drive_service, **kwargs):
    try:
        section_name = kwargs.get("section_name", "")
        user_input = kwargs.get("user_input", "")
        previous_response = kwargs.get("previous_response", "")
        agent, prompt, user_prompt = await prepare_agent_and_prompt(drive_service, **kwargs)

        if section_name and user_input and previous_response:
            agent.previous_response = previous_response
            agent.add_to_knowledge(section_name, user_input)

        knowledgebase_context = ""
        user_feedbacks = ""
        if not user_input:
            embedding_search_query = f"Function Analysis Report {kwargs.get("parent_entity", "")} and {kwargs.get("associate_enterprise", "")}."
            knowledgebase_context, user_feedbacks = await fetch_filtered_knowledge(embedding_search_query)

            if not knowledgebase_context:
                yield {
                    "content": "No relevant knowledge found in the database."
                }
            else:
                async for chunk in execute_search_and_generate_response_stream(knowledge_context=knowledgebase_context,
                                                                               combined_prompt=user_prompt if user_prompt else prompt,
                                                                               agent=agent,
                                                                               user_feedbacks=user_feedbacks):
                    yield chunk
    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


async def ask_fouray_legal_gv(drive_service, **kwargs):
    try:
        section_name = kwargs.get("section_name", "")
        user_input = kwargs.get("user_input", "")
        previous_response = kwargs.get("previous_response", "")
        agent, prompt, user_prompt = await prepare_agent_and_prompt(drive_service, **kwargs)

        if section_name and user_input and previous_response:
            agent.previous_response = previous_response
            agent.add_to_knowledge(section_name, user_input)

        knowledgebase_context = ""
        user_feedbacks = ""
        if not user_input:
            embedding_search_query = f"Function Analysis Report {kwargs.get("parent_entity", "")} and {kwargs.get("associate_enterprise", "")}."
            knowledgebase_context, user_feedbacks = await fetch_filtered_knowledge(embedding_search_query)

            if not knowledgebase_context:
                return {
                    "content": "No relevant knowledge found in the database."
                }
            else:
                return await execute_search_and_generate_response(knowledge_context=knowledgebase_context,
                                                                  combined_prompt=user_prompt if user_prompt else prompt,
                                                                  agent=agent, user_feedbacks=user_feedbacks)
    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


# -------------------- Utility Functions --------------------


async def fetch_filtered_knowledge(prompt=""):
    """Fetch knowledge from vector DB asynchronously."""
    current_user = loggedin_user_var.get()
    dim3_value = current_user.dim3
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.vector, VECTOR_SEARCH_LIMIT)
    agent_manager = AgentManager()

    try:
        async def search_knowledge():
            # query_agent = await agent_manager.get_vector_query_agent()
            # response = await asyncio.to_thread(query_agent.run, query + "\n\nGenerate vector search query")
            # prompt = response.content
            # print("- generated vector search: " + prompt)
            # prompt = "Function Analysis Report MNO Life science Private Limited (MNO India) and MNO Life science Inc. (MNO USA)."
            vector_db.default_limit = VECTOR_SEARCH_LIMIT
            vector_db.search_type = SearchType.vector
            vector_db.vector_score_weight = 1.0
            return await asyncio.to_thread(vector_db.vector_search, query=prompt)

        search_results = await search_knowledge()
        chunks = []
        user_feedbacks = []
        sep: str = "\n------------\n"
        for d in search_results:
            try:
                payload = json.loads(d.content)
                section_name = payload.get("section_name", "").strip()
                previous_response = payload.get("previous_response", "").strip()
                user_feedback = payload.get("user_feedback", "").strip()

                user_feedbacks.append(f"### Feedback from user:\n"
                                      f"- **section_name (function name):** {section_name}\n"
                                      f"- **previous_response:** {previous_response}\n"
                                      f"- **user_feedback:** {user_feedback}\n")
            except Exception:
                chunks.append(d.content)  # fallback for non‑JSON docs
        return sep.join(chunks), sep.join(user_feedbacks)

    except Exception as e:
        raise InternalServerErrorException(f"Error fetching knowledge: {str(e)}")


def extract_json(result: str):
    """Extract and return valid JSON response."""
    result = result.strip().strip("`").strip("json").strip()
    json_match = re.search(r"({.*})", result, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            raise InternalServerErrorException("Error parsing JSON response")
    return result.strip()


def format_prompt(knowledge_context, combined_prompt, user_feedbacks):
    prompt = ""
    if knowledge_context:
        prompt += f"\n\n## Knowledge Base:\n{knowledge_context}"
    if combined_prompt:
        prompt += f"\n\n## Query:\n{combined_prompt}"
    if user_feedbacks:
        prompt += f"\n\n## User Feedback from previous conversation:\n{user_feedbacks}"
    return prompt


async def execute_search_and_generate_response_stream(knowledge_context: Optional[str] = None,
                                                      combined_prompt: Optional[str] = None, agent: Agent = None,
                                                      user_feedbacks: str = ""):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """

    agent.search_knowledge = False
    prompt = format_prompt(knowledge_context, combined_prompt, user_feedbacks)

    try:
        buffer = ""
        inside_array = False
        brace_depth = 0
        object_buffer = ""
        # This will return an iterator (not async)
        for chunk in agent.run(prompt, stream=True):
            # if hasattr(chunk, "content"):
            #     yield chunk.content  # Working
            # await asyncio.sleep(0)  # Let the event loop breathe
            value = getattr(chunk, "content", chunk)
            if not isinstance(value, str):
                continue

            buffer += value

            # Check for beginning of array
            if not inside_array and "[" in buffer:
                inside_array = True
                buffer = buffer.split("[", 1)[1]  # Drop everything before `[` (start of array)
                continue

            if inside_array:
                for char in value:
                    if char == "{":
                        if brace_depth == 0:
                            object_buffer = ""  # Start new object
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
                                # Optional: log parsing error
                                pass
                            object_buffer = ""  # Reset for next object
                    elif brace_depth > 0:
                        object_buffer += char

            await asyncio.sleep(0)  # Yield control to event loop

    except Exception as e:
        raise InternalServerErrorException(f"Streaming error: {str(e)}")


async def execute_search_and_generate_response(knowledge_context: Optional[str] = None,
                                               combined_prompt: Optional[str] = None, agent: Agent = None,
                                               user_feedbacks: str = ""):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """
    agent.search_knowledge = False
    prompt = format_prompt(knowledge_context, combined_prompt, user_feedbacks)

    # Run the agent asynchronously
    result = await asyncio.to_thread(agent.run, prompt)
    if not IS_PROD:
        print(result.content)
    try:
        return extract_json(result.content)
    except json.JSONDecodeError:
        raise InternalServerErrorException("Error parsing JSON response")
