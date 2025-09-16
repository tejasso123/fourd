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
INSTRUCTION_COMMAND_FOLDER_NAME = "Blog"
OPENAI_MODEL = settings.OPENAI_MODEL
NUM_HISTORY_RESPONSES = settings.NUM_HISTORY_RESPONSES
VECTOR_SEARCH_LIMIT = settings.VECTOR_SEARCH_LIMIT
OPENAI_TEMP = 0.5
TOP_P = 0.9
IS_PROD = settings.ENV == "prod"
CACHED_FILES = {
    "blog_agent_config": "Agent_configuration_topic_map.md",
    "blog_best_practise": "keyword_cluster_map_bp.md",
    "blog_content_generation_prompt": "prompt_master_content_generation.md",
    "blog_topic_generation_prompt": "prompt_master_Semantic_TopicMap_Generator_v1.md",
    "blog_semantic_keyword_cluster_prompt": "prompt_master_SemanticKeywordCluster_ByBlogType_v1.md"
}


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


# -------------------- Initialize AI Agent --------------------

async def get_agent(session_id: Optional[str], agent_id: Optional[str]) -> Agent:
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
        num_memories=2,
    )

    return Agent(
        name="semantic_blog_writer",
        description="Writes structured blog content using vector clustering and search intent mapping.",
        task="Generate JSON-based blog outlines with entity-aligned H2s, intent tags, and grounded reference points.",
        prevent_hallucinations=True,
        knowledge=AgentKnowledge(vector_db=vector_db),
        storage=storage,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        add_context=True,
        markdown=True,
        add_chat_history_to_messages=False,
        read_chat_history=False,
        # num_history_responses=NUM_HISTORY_RESPONSES,
        num_history_responses=0,
        debug_mode=not IS_PROD,
        prevent_prompt_leakage=True,
        parse_response=True,
        structured_outputs=True,
        search_knowledge=False,
        memory=memory
    )


# -------------------- Shared Prep Logic --------------------

async def prepare_agent_and_prompt(drive_service, **kwargs):
    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)

    agent = await get_agent(kwargs.get("session_id"), kwargs.get("agent_id"))

    agent.model = OpenAIChat(
        id=settings.OPENAI_LOWER_MODEL,
        model=settings.OPENAI_LOWER_MODEL,
        max_completion_tokens=10000,
        temperature=OPENAI_TEMP,
        api_key=OPENAI_API_KEY,
        top_p=TOP_P,
        user=user_id,
        session_id=kwargs.get("session_id"),
        response_format={"type": "json_object"}
    )

    cached_content = await load_instructions_and_commands(drive_service)

    formatted_prompt = ""
    if kwargs.get("step") == 1:  # keyword cluster by blog type
        format_args = {
            "seed_keywords": kwargs.get("seed_keywords", ""),
            "blog_type": kwargs.get("blog_type", "")
        }
        formatted_prompt = cached_content[f"blog_semantic_keyword_cluster_prompt"].format(**format_args)
        agent.expected_output = settings.BLOG_SEMANTIC_KEYWORD_CLUSTER_EXPECTED_OUTPUT
    elif kwargs.get("step") == 2:  # semantic topic map
        format_args = {
            "blog_about": kwargs.get("blog_about", ""),
            "tone": kwargs.get("tone_of_voice", ""),
            "blog_length": kwargs.get("blog_length", ""),
            "location": kwargs.get("location_focus", ""),
            "language": kwargs.get("language", ""),
            "further_detail": kwargs.get("further_details", ""),
            "semantic_clusters": kwargs.get("semantic_clusters", ""),
        }
        formatted_prompt = cached_content[f"blog_topic_generation_prompt"].format(**format_args)
        agent.expected_output = settings.BLOG_TOPIC_GENERATION_EXPECTED_OUTPUT
    elif kwargs.get("step") == 3:  # content generation
        format_args = {
            "blog_about": kwargs.get("blog_about", ""),
            "tone": kwargs.get("tone_of_voice", ""),
            "blog_length": kwargs.get("blog_length", ""),
            "location": kwargs.get("location_focus", ""),
            "language": kwargs.get("language", ""),
            "topic_map": kwargs.get("topic_map", ""),
            # "company_transcripts": kwargs.get("company_transcripts", ""),
            "brand_context": kwargs.get("brand_context", ""),
            "image_guidelines": kwargs.get("image_guidelines", ""),
            "further_detail": kwargs.get("further_details", ""),
            "writing_tone": "Conversational, engaging, and easy to follow"
        }
        formatted_prompt = cached_content[f"blog_content_generation_prompt"].format(**format_args)
        agent.expected_output = settings.BLOG_CONTENT_GENERATION_EXPECTED_OUTPUT

    agent.guidelines = cached_content[f"blog_best_practise"]
    agent.system_prompt = cached_content[f"blog_agent_config"]

    return agent, formatted_prompt


# -------------------- AI Query Execution --------------------

async def ask_fouray_blog_stream(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        # to get uid from kwargs
        uid = kwargs.get("uid", None)
        agent, prompt = await prepare_agent_and_prompt(drive_service, **kwargs)

        knowledgebase_context = ""
        if uid:
            filters = {"uid": uid}
            knowledgebase_context = await fetch_filtered_knowledge(filters=filters, is_vector_search=False)

        async for chunk in execute_search_and_generate_response_stream(knowledge_context=knowledgebase_context,
                                                                       combined_prompt=prompt,
                                                                       agent=agent):
            yield chunk

    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


async def ask_fouray_blog(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        # to get uid from kwargs
        uid = kwargs.get("uid", None)
        agent, prompt = await prepare_agent_and_prompt(drive_service, **kwargs)

        knowledgebase_context = ""
        if uid:
            filters = {"uid": uid}
            knowledgebase_context = await fetch_filtered_knowledge(filters=filters, is_vector_search=False)

        return await execute_search_and_generate_response(knowledge_context=knowledgebase_context,
                                                          combined_prompt=prompt,
                                                          agent=agent)
    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


# -------------------- Utility Functions --------------------


async def fetch_filtered_knowledge(filters=None, is_vector_search=False):
    """Fetch knowledge from vector DB asynchronously."""
    current_user = loggedin_user_var.get()
    dim3_value = current_user.dim3
    # vector_db = PgVector(table_name=dim3_value, db_url=SYNC_DB_STR, search_type=SearchType.keyword, schema="ai")
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.keyword, VECTOR_SEARCH_LIMIT)

    try:
        async def search_knowledge():
            if is_vector_search:
                vector_db.default_limit = VECTOR_SEARCH_LIMIT
                vector_db.search_type = SearchType.vector
                vector_db.vector_score_weight = 1.0
                vector_db.filters_args = filters
                return await asyncio.to_thread(vector_db.vector_search, query="")
            else:
                vector_db.default_limit = VECTOR_SEARCH_LIMIT
                vector_db.search_type = SearchType.keyword
                vector_db.vector_score_weight = 0.0
                vector_db.filters_args = filters
                return await asyncio.to_thread(vector_db.keyword_search, query="")

        search_results = await search_knowledge()
        sep = "\n------------\n"
        chunks = [chunk.content for chunk in search_results]
        return sep.join(chunks)

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


async def execute_search_and_generate_response(knowledge_context: Optional[str] = None,
                                               combined_prompt: Optional[str] = None, agent: Agent = None):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """
    prompt = format_prompt(knowledge_context, combined_prompt)

    try:
        # Run the agent asynchronously
        result = await asyncio.to_thread(agent.run, prompt)
        if not IS_PROD:
            print(result.content)
    except Exception as e:
        raise InternalServerErrorException(f"Error running agent: {str(e)}")
    try:
        return extract_json(result.content)
    except json.JSONDecodeError:
        raise InternalServerErrorException("Error parsing JSON response")
