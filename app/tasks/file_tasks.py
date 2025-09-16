import base64
import os
import asyncio

from app.celery_app import mk_celery
from app.services.file_service import process_file

from app.utils.file_helper import remove_file


@mk_celery.task(name="app.tasks.process_file_task")
def process_file_task(file_content: str, file_path: str, file_extension: str,
                      is_file_already_saved: bool = True,
                      filters: dict = None,
                      dim3_value: str = None):
    """
    Celery Background task to decode, save, and process a single file asynchronously.
    """

    # Decode base64 file content
    file_data = base64.b64decode(file_content)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Write file to disk synchronously
    with open(file_path, "wb") as out_file:
        out_file.write(file_data)

    # Run the async function inside a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(
        process_file(
            file=file_path,
            file_extension=file_extension,
            is_file_already_saved=is_file_already_saved,
            filters=filters,
            dim3_value=dim3_value
        )
    )

    loop.run_until_complete(remove_file(file_path))  # Cleanup after processing
    loop.close()

    # Clean up the file after processing
    if os.path.exists(file_path):
        os.remove(file_path)
