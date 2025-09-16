import json
import asyncio
import re
from typing import Optional
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.knowledge.agent import AgentKnowledge
from phi.vectordb.pgvector import SearchType
from app.core.context import loggedin_user_var
from app.core import settings
from app.services.storage_cache import get_cached_storage, get_cached_custom_vector_db
from app.core.exceptions import InternalServerErrorException

# -------------------- Environment Variables --------------------
OPENAI_API_KEY = settings.OPENAI_API_KEY
SYNC_DB_STR = settings.SYNC_DB_STR
OPENAI_MODEL = settings.OPENAI_MODEL
OPENAI_LOWER_MODEL = settings.OPENAI_LOWER_MODEL
NUM_HISTORY_RESPONSES = settings.NUM_HISTORY_RESPONSES
VECTOR_SEARCH_LIMIT = 10
OPENAI_TEMP = 0.2
TOP_P = 0.9
IS_PROD = settings.ENV == "prod"


# -------------------- Initialize AI Agent --------------------

async def get_agent(session_id: Optional[str], agent_id: Optional[str]) -> Agent:
    """Initialize the AI Agent asynchronously with knowledge and memory."""

    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)
    dim3_value = current_user.dim3
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.vector, VECTOR_SEARCH_LIMIT)
    storage = get_cached_storage(dim3_value)

    return Agent(
        name="free_chat_assistant",
        description="A general purpose AI assistant for free-form conversations with vector search capabilities.",
        task="Provide helpful responses to user queries using knowledge base search when appropriate.",
        prevent_hallucinations=True,
        knowledge=AgentKnowledge(vector_db=vector_db),
        storage=storage,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        add_context=True,
        search_knowledge=True,
        markdown=True,
        add_chat_history_to_messages=True,
        read_chat_history=True,
        num_history_responses=NUM_HISTORY_RESPONSES,
        debug_mode=not IS_PROD,
        prevent_prompt_leakage=True,
        parse_response=True,
        structured_outputs=True
    )


# -------------------- AI Query Execution --------------------

async def ask_fouray_free_chat_stream(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        uid = kwargs.get("uid", None)
        image_file = kwargs.get("image_file", None)
        further_details = kwargs.get("further_details", "")

        agent = await get_agent(kwargs.get("session_id"), kwargs.get("agent_id"))

        current_user = loggedin_user_var.get()
        user_id = str(current_user.id)

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

        knowledge_context = ""
        if uid:
            filters = {"uid": uid}
            knowledge_context = await fetch_filtered_knowledge(filters=filters)

        # Enable vector search in knowledge base
        agent.search_knowledge = True

        prompt = format_prompt(knowledge_context, further_details)

        images = []
        if image_file:
            images.append(image_file)

        async for chunk in execute_search_and_generate_response_stream(agent, prompt, images):
            yield chunk

    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


async def ask_fouray_free_chat(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        uid = kwargs.get("uid", None)
        image_file = kwargs.get("image_file", None)
        further_details = kwargs.get("further_details", "")

        agent = await get_agent(kwargs.get("session_id"), kwargs.get("agent_id"))

        current_user = loggedin_user_var.get()
        user_id = str(current_user.id)

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

        knowledge_context = ""
        if uid:
            filters = {"uid": uid}
            knowledge_context = await fetch_filtered_knowledge(filters=filters)

        # Enable vector search in knowledge base
        agent.search_knowledge = True

        prompt = format_prompt(knowledge_context, further_details)

        images = []
        if image_file:
            images.append(image_file)

        return await execute_search_and_generate_response(agent, prompt, images)

    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


# -------------------- Utility Functions --------------------

async def fetch_filtered_knowledge(filters=None, is_vector_search=False, vector_search_by=None):
    """Fetch knowledge from vector DB asynchronously."""
    current_user = loggedin_user_var.get()
    dim3_value = current_user.dim3
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.vector, VECTOR_SEARCH_LIMIT)

    try:
        async def search_knowledge():
            if is_vector_search:
                vector_db.default_limit = 5
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


def format_prompt(knowledge_context, user_query):
    """Format the prompt with knowledge context and user query."""
    prompt = ""
    if knowledge_context:
        prompt += f"\n\n## Knowledge Base Context:\n{knowledge_context}"
    if user_query:
        prompt += f'''\n\n## User Query:\n{user_query}\n\n
                \n If images are attached then pls take it as reference and follow user instructions
                \n Please respond in JSON format, given below \n 
                {{
                  "response": [
                    {{
                      "component_name": "answer",
                      "value": "{{Generated string type answer}}"
                    }}
                  ] 
                }}.'''
    return prompt


async def execute_search_and_generate_response_stream(agent: Agent = None, prompt: Optional[str] = None,
                                                      images: Optional[str] = None, ):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """
    agent.search_knowledge = False

    try:
        import gc
        gc.collect()
        print("Memory clean up before streaming")

        buffer = ""
        inside_array = False
        brace_depth = 0
        object_buffer = ""
        # This will return an iterator (not async)
        for chunk in agent.run(prompt, images=images, stream=True):

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


async def execute_search_and_generate_response(agent: Agent, prompt: str, images: list = None):
    """
    Execute agent response with vector search enabled.
    """
    try:
        # Run the agent asynchronously
        result = await asyncio.to_thread(agent.run, prompt, images=images or [])
        if not IS_PROD:
            print(result.content)
        return extract_json(result.content)
    except Exception as e:
        raise InternalServerErrorException(f"Error running agent: {str(e)}")
