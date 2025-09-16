import os
import os
from app.utils.redis_client import redis_client
from app.core.exceptions import InternalServerErrorException
import asyncio
from app.core import settings


async def update_redis_from_drive():
    from app.services.drive_service import get_google_drive_service_for_system, fetch_drive_file_content
    """
    Update Redis asynchronously with the latest files from Google Drive.
    """
    # Environment variables
    instruction_command_folder_name = settings.INSTRUCTIONS_AND_COMMANDS_FOLDER_NAME
    instructions_file_name = settings.INSTRUCTIONS_FILE_NAME
    commands_file_name = settings.COMMANDS_FILE_NAME
    product_sections = settings.PRODUCT_SECTIONS

    try:
        drive_service = await get_google_drive_service_for_system()

        instructions_key = "instructions_content"
        commands_key = "commands_content"

        cached_instructions_content = await fetch_drive_file_content(
            drive_service, instructions_file_name, instruction_command_folder_name
        )

        cached_commands_content = await fetch_drive_file_content(
            drive_service, commands_file_name, instruction_command_folder_name
        )

        # Async cache to Redis
        await asyncio.gather(
            redis_client.set_value_async(instructions_key, cached_instructions_content),
            redis_client.set_value_async(commands_key, cached_commands_content)
        )

        # # Update section-wise content concurrently
        sections = product_sections.split(",")
        for section in sections:
            section_name = section.strip()
            sectional_instructions_key = f"{section_name}_instructions_content"
            sectional_commands_key = f"{section_name}_commands_content"

            # Fetch and cache section wise instructions content
            sectional_cached_instructions_content = await fetch_drive_file_content(
                drive_service, f"{section_name}_instructions.md", instruction_command_folder_name
            )

            # Fetch and cache section wise instructions content
            sectional_cached_commands_content = await fetch_drive_file_content(
                drive_service, f"{section_name}_commands.md", instruction_command_folder_name
            )
            await asyncio.gather(
                redis_client.set_value_async(sectional_instructions_key, sectional_cached_instructions_content),
                redis_client.set_value_async(sectional_commands_key, sectional_cached_commands_content)
            )

    except Exception as e:
        print(f"Error updating Redis from Drive: {str(e)}")
