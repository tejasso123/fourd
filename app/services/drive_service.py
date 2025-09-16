import os
import asyncio
import json
import aiofiles
# from cryptography.fernet import Fernet
from fastapi import APIRouter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from app.core.exceptions import InternalServerErrorException, ResourceNotFoundException
from app.utils.file_helper import remove_file

# from app.services import process_file
# from app.utils import redis_client

router = APIRouter()

TEMP_FOLDER = './temp_files'
SECRETS_FOLDER = 'app/secrets'


# -------------------- Google Drive Async Service --------------------

async def get_google_drive_service(access_token: str):
    """Build and return Google Drive service asynchronously."""
    creds = Credentials(token=access_token)
    return build("drive", "v3", credentials=creds)


async def get_google_drive_service_for_system():
    """Get authenticated Google Drive service using a service account."""
    try:

        service_account_json_str = os.getenv("SERVICE_ACCOUNT_JSON")
        if not service_account_json_str:
            raise InternalServerErrorException("Service account JSON not found in environment variables.")

        service_account_json = json.loads(service_account_json_str)

        # Ensure the secrets directory exists
        os.makedirs(SECRETS_FOLDER, exist_ok=True)

        service_account_file_path = os.path.join(SECRETS_FOLDER, 'service_account.json')

        # Write JSON to file asynchronously
        async with aiofiles.open(service_account_file_path, 'w') as file:
            await file.write(json.dumps(service_account_json))

        # Authenticate with Google API
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file_path,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=credentials)

        return service

    except Exception as e:
        raise InternalServerErrorException(f"Google Drive Authentication Failed: {str(e)}")


# # -------------------- File Handling --------------------
#
# async def process_file_from_drive(service, file, dim3_value):
#     """Download and process a Google Drive file asynchronously."""
#     try:
#         request = service.files().get_media(fileId=file['id'])
#         file_data = await asyncio.to_thread(request.execute)  # Run in thread pool
#
#         # Save file asynchronously
#         temp_path = f"{TEMP_FOLDER}/{file['name']}"
#         async with aiofiles.open(temp_path, "wb") as temp_file:
#             await temp_file.write(file_data)
#
#         file_extension = file['name'].rsplit('.', 1)[1].lower()
#
#         # Save to Vector DB and Knowledgebase
#         await process_file(temp_path, file_extension=file_extension, is_file_already_saved=True, dim3_value=dim3_value)
#
#     except Exception as e:
#         raise InternalServerErrorException("Failed to process file {file['name']}: {str(e)}")
#
#
# # -------------------- Google Drive File Management --------------------
#
# async def list_files_from_folder(service, folder_id=None):
#     """List all files in a specific Google Drive folder asynchronously."""
#     try:
#         query = f"'{folder_id}' in parents" if folder_id else "trashed = false"
#         results = await asyncio.to_thread(service.files().list, q=query, pageSize=1000,
#                                           fields="files(id, name, mimeType, parents, modifiedTime)")
#         return results.get('files', [])
#
#     except HttpError as error:
#         raise InternalServerErrorException(f"Google Drive Error: {error}")
#
#

async def get_folder_id_by_name(service, folder_name):
    """Retrieve Google Drive folder ID by folder name asynchronously."""

    try:
        if not folder_name:
            return None

        parts = folder_name.strip("/").split("/")

        # Get all folders
        result = await asyncio.to_thread(
            lambda: service.files().list(
                q="mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="files(id, name, parents)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
        )
        folders = result.get("files", [])

        if not folders:
            return None

        parent_id = "root"
        for part in parts:
            found = False
            for folder in folders:
                folder_parents = folder.get("parents", [])
                if folder["name"].strip() == part and (
                        not folder_parents and parent_id == "root" or parent_id in folder_parents):
                    parent_id = folder["id"]
                    found = True
                    break
            if not found:
                print(f"Folder not found in path: {part}")
                return None

        return parent_id
    except HttpError as e:
        raise InternalServerErrorException(f"Google Drive Error: {str(e)}")


async def fetch_drive_file_content(service, file_name, folder_name):
    """Fetch content of a file from Google Drive asynchronously."""
    try:
        # Get folder ID
        folder_id = await get_folder_id_by_name(service, folder_name)
        if not folder_id:
            raise ResourceNotFoundException(f"Folder '{folder_name}' not found.")

        # Get file ID
        file_query = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
        # file_results = await asyncio.to_thread(service.files().list, q=file_query, fields="files(id)").execute()
        file_results = await asyncio.to_thread(
            lambda: service.files().list(q=file_query, fields="files(id)").execute()
        )
        file_id = file_results["files"][0]["id"] if file_results["files"] else None

        if not file_id:
            raise ResourceNotFoundException(f"File '{file_name}' not found in folder '{folder_name}'.")

        # Retrieve file content
        request = service.files().get_media(fileId=file_id)
        file_content = await asyncio.to_thread(request.execute)

        return file_content.decode("utf-8")

    except Exception as e:
        raise InternalServerErrorException(f"Error fetching file '{file_name}' from Google Drive: {str(e)}")

#
# # -------------------- Redis Update --------------------
#
# async def update_redis_from_drive():
#     """Update Redis with the latest files from Google Drive asynchronously."""
#     try:
#         # Environment variables
#         instruction_command_folder_name = os.getenv("INSTRUCTIONS_AND_COMMANDS_FOLDER_NAME")
#         instructions_file_name = os.getenv("INSTRUCTIONS_FILE_NAME")
#         commands_file_name = os.getenv("COMMANDS_FILE_NAME")
#         product_sections = os.getenv("PRODUCT_SECTIONS")
#
#         # Get Google Drive service
#         drive_service = await get_google_drive_service_for_system()
#
#         # Keys for Redis cache
#         instructions_key = "instructions_content"
#         commands_key = "commands_content"
#
#         # Fetch and cache instructions content
#         cached_instructions_content = await fetch_drive_file_content(
#             drive_service, instructions_file_name, instruction_command_folder_name
#         )
#         redis_client.set_value(instructions_key, cached_instructions_content)
#
#         # Fetch and cache commands content
#         cached_commands_content = await fetch_drive_file_content(
#             drive_service, commands_file_name, instruction_command_folder_name
#         )
#         redis_client.set_value(commands_key, cached_commands_content)
#
#         # Update section-wise content
#         sections = product_sections.split(",")
#         for section in sections:
#             section_name = section.strip()
#             sectional_instructions_key = f"{section_name}_instructions_content"
#             sectional_commands_key = f"{section_name}_commands_content"
#
#             # Fetch and cache section-wise instructions content
#             sectional_cached_instructions_content = await fetch_drive_file_content(
#                 drive_service, f"{section_name}_instructions.md", instruction_command_folder_name
#             )
#             redis_client.set_value(sectional_instructions_key, sectional_cached_instructions_content)
#
#             # Fetch and cache section-wise commands content
#             sectional_cached_commands_content = await fetch_drive_file_content(
#                 drive_service, f"{section_name}_commands.md", instruction_command_folder_name
#             )
#             redis_client.set_value(sectional_commands_key, sectional_cached_commands_content)
#
#     except Exception as e:
#         raise InternalServerErrorException("Redis Update Failed: {str(e)}")

from mimetypes import guess_type
import base64

async def fetch_all_image_links_from_drive_folder(service, folder_path: str, allowed_extensions=None) -> list[str]:
    """
    Fetches and returns public viewable links to all image files from a specific Google Drive folder.
    """
    if allowed_extensions is None:
        allowed_extensions = {'.webp', '.jpg', '.jpeg', '.png'}

    try:
        folder_id = await get_folder_id_by_name(service, folder_path)
        if not folder_id:
            raise ResourceNotFoundException(f"Folder '{folder_path}' not found.")

        query = f"'{folder_id}' in parents and trashed = false"
        results = await asyncio.to_thread(
            lambda: service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
        )

        files = results.get("files", [])
        image_links = []

        for file in files:
            ext = os.path.splitext(file["name"])[1].lower()
            if ext in allowed_extensions:
                # Make the file shareable
                # await asyncio.to_thread(lambda: service.permissions().create(
                #     fileId=file["id"],
                #     body={"role": "reader", "type": "anyone"},
                #     fields="id"
                # ).execute())

                # Generate shareable viewable link
                # image_link = f"https://drive.google.com/uc?export=view&id={file['id']}"
                image_link = f"https://fouray-development.s3.us-east-1.amazonaws.com/{folder_path}/{file['name']}"
                image_links.append(image_link)

        return image_links

    except Exception as e:
        raise InternalServerErrorException(f"Error fetching image links from folder '{folder_path}': {str(e)}")
