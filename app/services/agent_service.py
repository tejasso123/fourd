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
INSTRUCTION_COMMAND_FOLDER_NAME = settings.INSTRUCTIONS_AND_COMMANDS_FOLDER_NAME
INSTRUCTIONS_FILE = settings.INSTRUCTIONS_FILE_NAME
COMMANDS_FILE = settings.COMMANDS_FILE_NAME
OPENAI_MODEL = settings.OPENAI_MODEL
OPENAI_LOWER_MODEL = settings.OPENAI_LOWER_MODEL
OPENAI_TEMP = settings.OPENAI_TEMP
TOP_P = settings.TOP_P
NUM_HISTORY_RESPONSES = settings.NUM_HISTORY_RESPONSES
VECTOR_SEARCH_LIMIT = settings.VECTOR_SEARCH_LIMIT
IS_PROD = settings.ENV == "prod"
CACHED_FILES = {
    "product_instructions_content": "product_instructions_content.md",
    "product_commands_content": "product_commands_content.md"
}


# -------------------- Async Load Instructions & Commands --------------------

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


async def load_instructions_and_commands_for_sectional(drive_service, section_name: str):
    """
    Load commands for a specific section from Google Drive if not cached in Redis.
    """
    sectional_commands_key = f"product_{section_name}_commands_content"

    # Check Redis cache asynchronously
    sectional_cached_commands_content = await redis_client.get_value_async(sectional_commands_key)

    if sectional_cached_commands_content is None:
        sectional_cached_commands_content = await fetch_drive_file_content(
            drive_service, f"{sectional_commands_key}.md", INSTRUCTION_COMMAND_FOLDER_NAME
        )
        await redis_client.set_value_async(sectional_commands_key, sectional_cached_commands_content)

    return sectional_cached_commands_content


# -------------------- Initialize AI Agent --------------------

async def get_agent(session_id: Optional[str], agent_id: Optional[str]) -> ProductDescriptionAgent:
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

    return ProductDescriptionAgent(
        name="product_description_writer",
        description="Creates high-converting product descriptions by combining keyword relevance, buyer intent, and structured formatting.",
        task="Generate SEO-optimized product descriptions in JSON format with clear feature-benefit mapping, target audience alignment, and grounded contextual data.",
        prevent_hallucinations=True,
        knowledge=AgentKnowledge(vector_db=vector_db),
        storage=storage,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        add_context=True,
        markdown=True,
        add_chat_history_to_messages=True,
        read_chat_history=True,
        num_history_responses=NUM_HISTORY_RESPONSES,
        debug_mode=not IS_PROD,
        prevent_prompt_leakage=True,
        parse_response=True,
        structured_outputs=True,
        memory=memory,
        guidelines=[
            "User feedback takes priority over all previous instructions. If the user requests a different word count, tone, or style, strictly follow the User feedback",
            "Always start with an emotional hook that reflects the customer's pain point or desire.",
            "Use benefit-first language — emphasize what the product does for the customer, not just what it is.",
            "Use persuasive, confidence-building tone: clear, trustworthy, and empathetic.",
            "Include sensory or relief-oriented words like 'soothing', 'refreshing', 'gentle', 'fast-acting', 'lasting'.",
            "Avoid generic terms (e.g., 'good product'); always be specific (e.g., 'relieves acidity within 15 minutes').",
            "Back claims with credibility phrases like 'clinically proven', 'trusted by experts', 'Ayurvedic formulation'.",
            "Target the buyer’s lifestyle and situation (e.g., busy professionals, natural wellness seekers, etc.).",
            "Ensure structure: title, teaser, 5 highlights, description, ingredient-benefit mapping, and detailed how-to-use.",
            "Use formatting that improves readability: bullet points, short paragraphs, and structured JSON chunks.",
            "Focus on emotional transformation: 'from discomfort to daily comfort', 'from burning sensation to calm stomach'.",
            "Include post-usage care tips to reflect holistic well-being and thoughtfulness.",
            "Mention dietary/lifestyle support tips to increase trust and show customer-centric care.",
            "Speak as if you’re guiding the customer, not just selling — be a helpful advisor.",
            "In ‘how_to_use’, include timing, routine, and precautions for safety and completeness.",
            "Avoid overpromising or making unverifiable claims (e.g., 'cures all diseases'). Stick to 'supports', 'reduces', etc.",
            "End descriptions with a subtle motivational nudge: 'Take control of your digestion — the natural way.'"
            "End with a subtle, persuasive call-to-action (e.g., 'Try it today')."
        ]
    )


# -------------------- Shared Prep Logic --------------------

async def prepare_agent_and_prompt(drive_service, **kwargs):
    current_user = loggedin_user_var.get()
    user_id = str(current_user.id)

    agent = await get_agent(kwargs.get("session_id"), kwargs.get("agent_id"))

    agent.model = OpenAIChat(
        id=OPENAI_MODEL,
        model=OPENAI_MODEL,
        max_completion_tokens=5000,
        temperature=OPENAI_TEMP,
        api_key=OPENAI_API_KEY,
        top_p=TOP_P,
        user=user_id,
        session_id=kwargs.get("session_id"),
        response_format={"type": "json_object"},
    )

    cached_content = await load_instructions_and_commands(drive_service)

    if kwargs.get("section_name"):
        sectional_commands_content = await load_instructions_and_commands_for_sectional(drive_service,
                                                                                        kwargs.get("section_name"))
        format_args = {
            "language": kwargs.get("language", ""),
            "location": kwargs.get("location", ""),
            "previous_response": kwargs.get("previous_response", ""),
            "further_details": kwargs.get("further_details", ""),
            "role": kwargs.get("role", ""),
            "goal": kwargs.get("goal", ""),
            "constraints": kwargs.get("constraints", ""),
            "keywords": kwargs.get("keywords", ""),
            "custom_section": kwargs.get("custom_section", ""),
        }
        agent.system_prompt = cached_content["product_instructions_content"].format(**format_args)
        formatted_prompt = sectional_commands_content.format(**format_args)
    else:
        format_args = {
            "language": kwargs.get("language", ""),
            "location": kwargs.get("location", ""),
            "keywords": kwargs.get("keywords", ""),
            "further_details": kwargs.get("further_details", "")
        }
        agent.system_prompt = cached_content["product_instructions_content"].format(**format_args)
        formatted_prompt = cached_content[f"product_commands_content"].format(**format_args)

    return agent, formatted_prompt


# -------------------- AI Query Execution --------------------

async def ask_fouray_product_description_stream(drive_service, **kwargs):
    """Process AI query asynchronously and return the response."""
    try:
        product_sku = kwargs.get("product_sku", "")
        section_name = kwargs.get("section_name", "")
        further_details = kwargs.get("further_details", "")
        previous_response = kwargs.get("previous_response", "")

        agent, prompt = await prepare_agent_and_prompt(drive_service, **kwargs)

        if section_name and further_details and previous_response:
            agent.filters_ags = {"sku": product_sku, "source": "user_feedback", "section_name": section_name}
            agent.previous_response = previous_response if previous_response else ""
            agent.add_to_knowledge(section_name, further_details)
            await asyncio.sleep(1)  # Allow time for knowledge to be added

        knowledgebase_context = ""
        if product_sku:
            filters = {"sku": product_sku}
            knowledgebase_context, user_feedbacks = await fetch_filtered_knowledge(filters=filters)
            if user_feedbacks:
                agent.additional_context = user_feedbacks

        async for chunk in execute_search_and_generate_response_stream(knowledge_context=knowledgebase_context,
                                                                       combined_prompt=prompt,
                                                                       agent=agent):
            yield chunk

    except Exception as e:
        raise InternalServerErrorException(f"Error while processing request: {str(e)}")


async def fetch_filtered_knowledge(filters=None):
    """Fetch knowledge from vector DB asynchronously."""
    current_user = loggedin_user_var.get()
    dim3_value = current_user.dim3
    vector_db = get_cached_custom_vector_db(dim3_value, SYNC_DB_STR, SearchType.keyword, VECTOR_SEARCH_LIMIT)

    try:
        async def search_knowledge():
            vector_db.default_limit = VECTOR_SEARCH_LIMIT
            vector_db.search_type = SearchType.keyword
            vector_db.vector_score_weight = 0.0
            vector_db.filters_args = filters
            return await asyncio.to_thread(vector_db.keyword_search, query="")

        search_results = await search_knowledge()
        chunks = []
        user_feedbacks = []
        sep = "\n------------\n"
        # chunks = [chunk.content for chunk in search_results]
        # return sep.join(chunks)
        for d in search_results:
            try:
                payload = json.loads(d.content)
                section_name = payload.get("section_name", "").strip()
                previous_response = payload.get("previous_response", "").strip()
                user_feedback = payload.get("user_feedback", "").strip()

                user_feedbacks.append(f"### Feedback from user:\n"
                                      f"- **component name:** {section_name}\n"
                                      f"- **Previous response:** {previous_response}\n"
                                      f"- **User feedback:** {user_feedback}\n")
            except Exception:
                chunks.append(d.content)  # fallback for non‑JSON docs
        return sep.join(chunks), sep.join(user_feedbacks)

    except Exception as e:
        raise InternalServerErrorException(f"Error fetching knowledge: {str(e)}")


def format_prompt(knowledge_context, combined_prompt, user_feedbacks):
    prompt = ""
    if knowledge_context:
        prompt += f"\n\n## Knowledge Base:\n{knowledge_context}"
    if combined_prompt:
        prompt += f"\n\n## Query:\n{combined_prompt}"
    if user_feedbacks:
        prompt += f"\n\n## User Feedback from previous conversation :\n{user_feedbacks}"
    return prompt


async def execute_search_and_generate_response_stream(knowledge_context: Optional[str] = None,
                                                      combined_prompt: Optional[str] = None, agent: Agent = None):
    """
    Integrates search results, runs the agent asynchronously, and parses the JSON response.
    """

    agent.search_knowledge = False
    prompt = format_prompt(knowledge_context, combined_prompt, agent.additional_context)

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
