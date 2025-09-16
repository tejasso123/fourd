# from phi.document.chunking.recursive import RecursiveChunking
# from phi.embedder.openai import OpenAIEmbedder
from phi.knowledge.pdf import PDFKnowledgeBase, PDFReader
from phi.knowledge.text import TextKnowledgeBase, TextReader
from phi.knowledge.docx import DocxKnowledgeBase, DocxReader
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.knowledge.csv import CSVKnowledgeBase, CSVReader
from phi.vectordb.pgvector import SearchType
import asyncio
from app.core import settings
from app.services.custom_web_reader import CustomWebsiteReader
from app.services.storage_cache import get_cached_custom_vector_db


async def load_knowledge_base(path_name, db_name, file_type, urls=None, filters=None):
    # vector_db = CustomPgVector(
    #     table_name=db_name,
    #     db_url=settings.SYNC_DB_STR,
    #     search_type=SearchType.vector,
    #     schema="ai",
    #     embedder=OpenAIEmbedder(model="text-embedding-3-large")
    # )
    vector_db = get_cached_custom_vector_db(dim3_value=db_name, sync_db_str=settings.SYNC_DB_STR,
                                            search_type=SearchType.vector)

    if file_type == 'pdf':
        reader = PDFReader(chunk=True, chunk_size=800)
        knowledge_base = PDFKnowledgeBase(path=path_name, vector_db=vector_db, reader=reader)
        # chunking_strategy=RecursiveChunking(chunk_size=1000, overlap=200))

    elif file_type == 'text':
        reader = TextReader(chunk=True, chunk_size=800)
        knowledge_base = TextKnowledgeBase(path=path_name, vector_db=vector_db, reader=reader)
    #                                            chunking_strategy=RecursiveChunking(chunk_size=1000, overlap=200))

    elif file_type == 'docx':
        reader = DocxReader(chunk=True, chunk_size=800)
        knowledge_base = DocxKnowledgeBase(path=path_name, vector_db=vector_db, reader=reader)
    #                                            chunking_strategy=RecursiveChunking(chunk_size=1000, overlap=200))

    elif file_type == 'web':
        reader = CustomWebsiteReader(chunk=True, chunk_size=800)
        knowledge_base = WebsiteKnowledgeBase(urls=urls, vector_db=vector_db, reader=reader, max_depth=1)
    #                                               chunking_strategy=RecursiveChunking(chunk_size=1000, overlap=200))

    elif file_type == 'csv':
        reader = CSVReader(chunk=True, chunk_size=800)
        knowledge_base = CSVKnowledgeBase(path=path_name, vector_db=vector_db,
                                          reader=reader)  # RecursiveChunking is overkill for row-wise structured data like CSVs hence default chunking strategy is used.

    else:
        raise ValueError("Unsupported file type")
    #
    # if filters.tags and isinstance(filters.tags, str):
    #     filters["tags"] = filters.tags.split(',') if filters else []

    # ✅ Async wrapper for IO-bound loading operation
    await asyncio.to_thread(knowledge_base.load, upsert=True, filters=filters)
