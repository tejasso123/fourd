import base64
import aiofiles.os
from pathlib import Path
import asyncio
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter
from app.services.knowledge_base_service import load_knowledge_base
from app.utils import save_file, preprocess_markdown, preprocess_text_using_openai, AgentManager
from app.utils.file_helper import remove_file, extract_docx_text_and_images_async, convert_image_to_base64
from docx import Document
import fitz
from PIL import Image
import os
import base64

manager_agent = AgentManager()


async def process_file(file, file_extension, is_file_already_saved=False, filters=None, dim3_value: str = None) -> None:
    path_name = file if is_file_already_saved else await save_file(file)

    if file_extension == 'pdf':
        text, images = await asyncio.to_thread(extract_from_pdf, path_name)

        txt_path = path_name.replace(Path(path_name).suffix, '.txt')
        async with aiofiles.open(txt_path, 'w', encoding='utf-8') as temp_file:
            await temp_file.write(text)
        await load_knowledge_base(txt_path, dim3_value, file_type='text', filters=filters)
        await remove_file(txt_path)

        # image processing
        for i, image_base64_string in enumerate(images):
            base, ext = os.path.splitext(txt_path)
            updated_txt_path = f"{base}_{i + 1}{ext}"
            await process_image(dim3_value, filters, updated_txt_path, image_base64_string)


    elif file_extension in {'txt', 'md'}:
        if file_extension == 'md':
            plain_text = await preprocess_markdown(path_name)
            cleaned_text = await preprocess_text_using_openai(plain_text)
            txt_path = path_name.replace('.md', '.txt')
            async with aiofiles.open(txt_path, 'w', encoding='utf-8') as temp_file:
                await temp_file.write(cleaned_text)
            await load_knowledge_base(txt_path, dim3_value, file_type='text', filters=filters)
            await remove_file(txt_path)
        else:
            await load_knowledge_base(path_name, dim3_value, file_type='text', filters=filters)

    elif file_extension in {'doc', 'docx'}:
        text, images = await extract_docx_text_and_images_async(path_name)
        txt_path = path_name.replace(Path(path_name).suffix, '.txt')

        async with aiofiles.open(txt_path, 'w', encoding='utf-8') as temp_file:
            await temp_file.write(text)
        await load_knowledge_base(txt_path, dim3_value, file_type='text', filters=filters)
        await remove_file(txt_path)

        # image processing
        for i, image_base64_string in enumerate(images):
            base, ext = os.path.splitext(txt_path)
            updated_txt_path = f"{base}_{i + 1}{ext}"
            await process_image(dim3_value, filters, updated_txt_path, image_base64_string)

    elif file_extension in {'csv', 'xls', 'xlsx'}:
        if file_extension == 'csv':
            await load_knowledge_base(path_name, dim3_value, file_type='csv', filters=filters)
        else:
            csv_file_path = await asyncio.to_thread(convert_excel_to_csv, path_name)
            await load_knowledge_base(csv_file_path, dim3_value, file_type='csv', filters=filters)
            await remove_file(csv_file_path)

    elif file_extension in {'jpg', 'jpeg', 'png'}:
        # await asyncio.to_thread(preprocess_image, path_name)
        await process_image(dim3_value, filters, path_name)


    elif file_extension in {'mp3', 'mp4', 'mpeg', 'mpga', 'wav', 'webm', 'm4a'}:
        summary = await manager_agent.summarize_audio(path_name)
        txt_path = path_name.replace(Path(path_name).suffix, '.txt')
        async with aiofiles.open(txt_path, 'w', encoding='utf-8') as temp_file:
            await temp_file.write(summary)
        await load_knowledge_base(txt_path, dim3_value, file_type='text', filters=filters)
        await remove_file(txt_path)

    else:
        raise ValueError("Unsupported file type")

    await remove_file(path_name)


async def process_image(dim3_value, filters, path_name, base64_image=None):
    if base64_image is None:
        base64_image = await asyncio.to_thread(convert_image_to_base64, Path(path_name))

    agent = await manager_agent.get_image_to_text_agent()
    response = None
    for _ in range(2):
        response = await asyncio.to_thread(agent.run,
                                           message="Analyze this image and return a description, extracted text, and any meaning or logic if present.",
                                           images=[base64_image]
                                           )
        if response.content and "unable to assist" not in response.content.lower():
            break
        await asyncio.sleep(1)
    txt_path = path_name.replace(Path(path_name).suffix, '.txt')
    async with aiofiles.open(txt_path, 'w', encoding='utf-8') as temp_file:
        await temp_file.write(response.content)
    await load_knowledge_base(txt_path, dim3_value, file_type='text', filters=filters)
    await remove_file(txt_path)


def convert_excel_to_csv(file_path):
    df = pd.read_excel(file_path)
    csv_file = file_path.rsplit('.', 1)[0] + '.csv'
    df.to_csv(csv_file, index=False)
    return csv_file


# def convert_image_to_base64(image_path):
#     mime_type = "image/png" if image_path.suffix.lower() == '.png' else "image/jpeg"
#     with open(image_path, 'rb') as img_file:
#         return f"data:{mime_type};base64,{base64.b64encode(img_file.read()).decode()}"


def preprocess_image(image_path):
    img = Image.open(image_path).convert('L')
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(2)
    img.save(image_path)


def extract_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    images = []

    for page in doc:
        text += page.get_text()
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            images.append(f"data:image/png;base64,{img_base64}")

    return text, images
