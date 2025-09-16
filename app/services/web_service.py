import aiofiles.os
import asyncio
from app.core.exceptions import InternalServerErrorException
from app.services.knowledge_base_service import load_knowledge_base
from app.utils import AgentManager
from app.utils.file_helper import remove_file
import tempfile

TEMP_FOLDER = "app/temp_files"
manager_agent = AgentManager()
unwanted_phrases = [
    "i'm unable to access external",
    "unable to access external",
    "unable to access",
    "can guide you",
    "how to extract and structure",
    "currently can't access",
    "access external websites",
    "help you understand what types of information"
]


async def process_web_urls(url, filters=None, dim3_value: str = None) -> None:
    try:

        agent = await manager_agent.get_webpage_summary_agent()
        content = ""
        max_retries = 3

        for attempt in range(max_retries):
            response = await asyncio.to_thread(agent.run,
                                               message=f"Use trafilatura_tools tool to scrape and extract content from and return only page related data not any in starting and ending : {url}")
            content = response.content or ""
            if not any(phrase in content.lower() for phrase in unwanted_phrases):
                break
            # take breath
            await asyncio.sleep(0)
        else:
            # If still unwanted after retries
            raise InternalServerErrorException("Unable to retrieve valid content from URL try again.")

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix=".txt") as tmp_file:
            tmp_file.write(content)
            path_name = tmp_file.name

        # async with aiofiles.open(path_name, 'w', encoding='utf-8') as temp_file:
        #     await temp_file.write(response.content)

        await load_knowledge_base(path_name, dim3_value, file_type='text', filters=filters)
        await remove_file(path_name)
    except Exception as e:
        raise InternalServerErrorException(f"Invalid request data: {str(e)}")
