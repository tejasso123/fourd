from functools import lru_cache
from typing import Any

from phi.embedder.openai import OpenAIEmbedder
from phi.reranker.cohere import CohereReranker
from phi.storage.agent.postgres import PgAgentStorage
from phi.memory.db.postgres import PgMemoryDb
from phi.vectordb.search import SearchType

from app.core import settings
from app.services.CustomPgVectorDb import CustomPgVector


@lru_cache(maxsize=10)
def get_cached_storage(dim3_value: str):
    return PgAgentStorage(
        db_url=settings.SYNC_DB_STR,
        table_name=f"{dim3_value}_h",
        schema="ai"
    )


@lru_cache(maxsize=10)
def get_cached_memory_db(dim3_value: str):
    return PgMemoryDb(
        db_url=settings.SYNC_DB_STR,
        table_name=f"{dim3_value}_m",
        schema='ai',

    )


@lru_cache(maxsize=10)
def get_cached_custom_vector_db(dim3_value: str, sync_db_str: str, search_type: SearchType, limit: int = 10,
                                filters: Any = None):
    return CustomPgVector(
        table_name=dim3_value,
        db_url=sync_db_str,
        schema="ai",
        search_type=search_type,
        embedder=OpenAIEmbedder(model="text-embedding-3-large"),
        default_limit=limit,
        filters=filters,
        reranker=CohereReranker(api_key=settings.COHERE_API_KEY)
    )
