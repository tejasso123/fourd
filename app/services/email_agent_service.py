import json
import asyncio
import re
# from pathlib import Path
from typing import Optional, List
from phi.agent import Agent
# from phi.memory import AgentMemory
# from phi.memory.agent import MemoryRetrieval
# from phi.memory.db.postgres import PgMemoryDb
from phi.model.openai import OpenAIChat
from phi.knowledge.agent import AgentKnowledge
# from phi.storage.agent.postgres import PgAgentStorage
from phi.vectordb.pgvector import SearchType
from app.core.context import loggedin_user_var
from app.services.drive_service import fetch_drive_file_content, fetch_all_image_links_from_drive_folder
from app.core import settings
from app.services.storage_cache import get_cached_storage, get_cached_custom_vector_db
from app.utils import redis_client
from app.core.exceptions import InternalServerErrorException, ResourceNotFoundException

# import time
# import os

# from app.utils.file_helper import convert_image_to_base64

# -------------------- Environment Variables --------------------
OPENAI_API_KEY = settings.OPENAI_API_KEY
SYNC_DB_STR = settings.SYNC_DB_STR
INSTRUCTION_COMMAND_FOLDER_NAME = "Email"
OPENAI_MODEL = settings.OPENAI_MODEL
OPENAI_LOWER_MODEL = settings.OPENAI_LOWER_MODEL
NUM_HISTORY_RESPONSES = settings.NUM_HISTORY_RESPONSES
VECTOR_SEARCH_LIMIT = 10
OPENAI_TEMP = 0.7
TOP_P = 0.8
IS_PROD = settings.ENV == "prod"
CACHED_FILES = {
    "email_instructions_content": settings.INSTRUCTIONS_FILE_NAME,
    "email_commands_content": settings.COMMANDS_FILE_NAME,
    "email_agent_config": "agent_configuration.md",
    # "email_agent_context": "agent_context.md",
    "email_agent_additional_context": "agent_additional_context.md"
}
folder_names = settings.EMAIL_FOLDERS


# -------------------- Async Load Instructions, Commands and SOPs --------------------
async def load_instructions_and_commands(drive_service):
    """Load instructions and commands from Google Drive or Redis Cache asynchronously."""

    content = {}
    for key, file_name in CACHED_FILES.items():
        cached_content = await redis_client.get_value_async(key)
        if cached_content is None:
            cached_content = await fetch_drive_file_content(drive_service, file_name,
                                                            f"{INSTRUCTION_COMMAND_FOLDER_NAME}")
            await redis_client.set_value_async(key, cached_content)
        content[key] = cached_content

    return content


async def load_sop_templates(drive_service, folder_name: str):
    """Load base64 images from Redis Cache or Google Drive asynchronously."""

    redis_key = f"email_sop_templates_{folder_name}"
    cached_images = await redis_client.get_value_async(redis_key)

    if cached_images is not None:
        try:
            images = json.loads(cached_images)
        except json.JSONDecodeError:
            images = []
    else:
        images = await fetch_all_image_links_from_drive_folder(
            drive_service, f"{INSTRUCTION_COMMAND_FOLDER_NAME}/{folder_name}"
        )
        await redis_client.set_value_async(redis_key, json.dumps(images))

    return images


# -------------------- Initialize AI Agent --------------------

async def get_agent(session_id: Optional[str], agent_id: Optional[str]) -> Agent:
    """Initialize the AI Agent asynchronously with knowledge and memory."""

    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)
    dim3_value = current_user.dim3
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.vector, VECTOR_SEARCH_LIMIT)
    storage = get_cached_storage(dim3_value)

    return Agent(
        name="email_ui_component_generator",
        description="Generates structured UI components from promotional email layout images.",
        task="Extract atomic UI blocks from uploaded email templates using predefined internal component schema.",
        prevent_hallucinations=True,
        knowledge=AgentKnowledge(vector_db=vector_db),
        storage=storage,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        add_context=True,
        # search_knowledge=False,
        markdown=True,
        add_chat_history_to_messages=False,
        read_chat_history=False,
        # update_knowledge=True,
        num_history_responses=0,
        debug_mode=not IS_PROD,
        prevent_prompt_leakage=True,
        parse_response=True,
        structured_outputs=True
    )


# -------------------- Shared Prep Logic --------------------

async def prepare_agent_and_prompt(drive_service, **kwargs):
    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)
    folder_name = kwargs.get("folder_name")

    agent_task = get_agent(kwargs.get("session_id"), kwargs.get("agent_id"))
    images_task = load_sop_templates(drive_service, folder_name)

    agent, sop_images_links = await asyncio.gather(agent_task, images_task)

    agent.model = OpenAIChat(
        id=OPENAI_MODEL,
        model=OPENAI_MODEL,
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
        "tone": kwargs.get("tone", ""),
        "occasion": kwargs.get("occasion", ""),
        "further_details": kwargs.get("further_details", "")
    }
    agent.instructions = [cached_content[f"email_instructions_content"]]
    formatted_prompt = cached_content[f"email_commands_content"].format(**format_args)

    agent.guidelines = cached_content[f"email_agent_additional_context"]
    agent.system_prompt = cached_content[f"email_agent_config"]
    agent.expected_output = settings.EMAIL_EXPECTED_OUTPUT
    # agent.agent_data = {"images": [sop_images]}

    # agent.read_chat_history = True
    # agent.add_chat_history_to_messages = True
    # agent.num_history_responses = NUM_HISTORY_RESPONSES

    return agent, formatted_prompt, sop_images_links


# -------------------- Folder Name Mapping --------------------


def normalize(text):
    return re.sub(r'[^a-z]', '', text.lower())  # removes underscores, uppercase, etc.


# Preprocess folders into mapping
folder_map = {
    normalize(folder.replace("_BP", "")): folder
    for folder in folder_names.split(",")
}

# Build a dynamic regex pattern from the normalized keys of folder_map
pattern = r"(" + "|".join(folder_map.keys()) + r")"


def get_folder_name_from_template(template_name: str) -> str:
    match = re.search(pattern, normalize(template_name))
    if match:
        key = match.group(1)
        return folder_map.get(key)
    return None


# -------------------- AI Query Execution --------------------

async def ask_fouray_email_stream(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        template = kwargs.get("template")
        uid = kwargs.get("uid", None)
        folder_name = get_folder_name_from_template(template)
        if not folder_name:
            raise ResourceNotFoundException(f"Folder not found for template: {template}")

        kwargs.update(folder_name=folder_name)

        agent, prompt, sop_images_links = await prepare_agent_and_prompt(drive_service, **kwargs)

        knowledge_context = ""
        if uid:
            filters = {"uid": uid}
            knowledge_context = await fetch_filtered_knowledge(filters=filters)

        search_query = folder_name + " best practises"
        filters = {"template": "best_practise"}
        best_practise_context = await fetch_filtered_knowledge(is_vector_search=True, vector_search_by=search_query,
                                                               filters=filters)

        template_link = kwargs.get("file", "")

        async for chunk in execute_search_and_generate_response_stream(knowledge_context, prompt, agent,
                                                                       template_link, sop_images_links,
                                                                       best_practise_context):
            yield chunk

    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


async def ask_fouray_email(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        template = kwargs.get("template")
        folder_name = get_folder_name_from_template(template)
        if not folder_name:
            raise ResourceNotFoundException(f"Folder not found for template: {template}")

        kwargs.update(folder_name=folder_name)

        agent, prompt, sop_images_links = await prepare_agent_and_prompt(drive_service, **kwargs)

        knowledge_context = await fetch_filtered_knowledge(filters={"template": template})

        search_query = folder_name + " best practises"
        best_practise_context = await fetch_filtered_knowledge(is_vector_search=True, vector_search_by=search_query,
                                                               filters={"template": "best_practise"})

        template_link = kwargs.get("file", "")

        return await execute_search_and_generate_response(knowledge_context, prompt, agent, template_link,
                                                          sop_images_links, best_practise_context)
    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


# -------------------- Utility Functions --------------------


async def fetch_filtered_knowledge(filters=None, is_vector_search=False, vector_search_by=None):
    """Fetch knowledge from vector DB asynchronously."""
    current_user = loggedin_user_var.get()
    dim3_value = current_user.dim3
    # vector_db = PgVector(table_name=dim3_value, db_url=SYNC_DB_STR, search_type=SearchType.keyword, schema="ai")
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.vector, VECTOR_SEARCH_LIMIT)

    try:
        async def search_knowledge():
            if is_vector_search:
                vector_db.default_limit = 1
                vector_db.search_type = SearchType.vector
                vector_db.vector_score_weight = 1.0
                vector_db.filters_args = filters
                return await asyncio.to_thread(vector_db.vector_search, query=vector_search_by)
            else:
                vector_db.default_limit = settings.VECTOR_SEARCH_LIMIT
                vector_db.search_type = SearchType.keyword
                vector_db.vector_score_weight = 0.0
                vector_db.filters_args = filters
                return await asyncio.to_thread(vector_db.keyword_search, query="")
                # if results and len(results) > 0:
                #     first_doc_name = results[0].name
                #     filtered_docs = [doc for doc in results if doc.name == first_doc_name]
                #     return sorted(filtered_docs, key=lambda d: d.meta_data.get("chunk", 0))
                # else:
                #     return []

        search_results = await search_knowledge()

        return "\n".join([doc.content for doc in search_results if hasattr(doc, "content")]) or ""

    except Exception as e:
        raise InternalServerErrorException(f"Error fetching knowledge: {str(e)}")


def extract_json(result: str):
    """Extract and return valid JSON response (object or array)."""
    result = result.strip().strip("`").strip("json").strip()
    json_match = re.search(r"(\{.*\}|\[.*\])", result, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError as e:
            raise InternalServerErrorException(f"Error parsing JSON response: {str(e)}")
    return result.strip()


def format_prompt(knowledge_context, combined_prompt, best_practise_context):
    prompt = ""
    if knowledge_context:
        prompt += f"\n\n## Knowledge Base:\n{knowledge_context}"
    if best_practise_context:
        prompt += f"\n\n## Best Practices:\n{best_practise_context}"
    if combined_prompt:
        prompt += f"\n\n## Query:\n{combined_prompt}"
    return prompt


async def execute_search_and_generate_response_stream(knowledge_context: Optional[str] = None,
                                                      combined_prompt: Optional[str] = None, agent: Agent = None,
                                                      template_link: Optional[str] = None,
                                                      sop_images_links: Optional[List[str]] = None,
                                                      best_practise_context: Optional[str] = None):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """

    agent.search_knowledge = False
    prompt = format_prompt(knowledge_context, combined_prompt, best_practise_context)

    try:
        # file_path = os.path.join(os.path.dirname(__file__), "../../static/taxonomy.jpg")
        # template = convert_image_to_base64(Path(file_path))

        del knowledge_context
        del combined_prompt
        del best_practise_context
        import gc
        gc.collect()
        print("Memory clean up before streaming")

        component_library_link = "https://fouray-development.s3.us-east-1.amazonaws.com/Email/Component_Reference.png"

        images = [template_link, component_library_link] + sop_images_links

        buffer = ""
        inside_array = False
        brace_depth = 0
        object_buffer = ""
        # This will return an iterator (not async)
        for chunk in agent.run(prompt, images=images, stream=True):
            # do not remove below comments, they are useful for debugging
            # if hasattr(chunk, "content"):
            #     yield chunk.content  # Working
            # await asyncio.sleep(0)  # Let the event loop breathe
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


async def execute_search_and_generate_response(knowledge_context: Optional[str] = None,
                                               combined_prompt: Optional[str] = None, agent: Agent = None,
                                               template_link: Optional[str] = None,
                                               sop_images_links: Optional[List[str]] = None,
                                               best_practise_context: Optional[str] = None):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """
    prompt = format_prompt(knowledge_context, combined_prompt, best_practise_context)

    # file_path = os.path.join(os.path.dirname(__file__), "../../static/taxonomy.jpg")
    # template = convert_image_to_base64(Path(file_path))

    component_library_link = "https://fouray-development.s3.us-east-1.amazonaws.com/Email/Component_Reference.png"

    images = [template_link, component_library_link] + sop_images_links

    try:
        # Run the agent asynchronously
        result = await asyncio.to_thread(agent.run, prompt, images=images)
        if not IS_PROD:
            print(result.content)
    except Exception as e:
        raise InternalServerErrorException(f"Error running agent: {str(e)}")
    try:
        return extract_json(result.content)
    except json.JSONDecodeError:
        raise InternalServerErrorException("Error parsing JSON response")
