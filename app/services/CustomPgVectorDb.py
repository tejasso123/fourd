from typing import Optional, Dict, Any, List
from phi.document import Document
from phi.vectordb.pgvector import PgVector
from sqlalchemy.sql.expression import bindparam, select, func
from phi.utils.log import logger
from hashlib import md5
from sqlalchemy.dialects import postgresql
from datetime import datetime, timezone


class CustomPgVector(PgVector):
    def __init__(self, *args, default_limit: int = 40, filters: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_limit = default_limit
        self.filters_args = filters

    def vector_search(self, query: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None):
        limit = self.default_limit
        filters = self.filters_args or {}
        docs = super().vector_search(query=query, limit=limit, filters=filters)
        print(f"📄 {len(docs)} documents fetched from vector DB (vector_search)")
        return docs

    def search(self, query: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None):
        limit = self.default_limit
        filters = self.filters_args or {}
        docs = super().search(query=query, limit=limit, filters=filters)
        print(f"📄 {len(docs)} documents fetched from vector DB (search)")
        return docs

    def keyword_search(self, query: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None):
        limit = self.default_limit
        filters = self.filters_args or {}
        docs = super().keyword_search(query=query, limit=limit, filters=filters)
        print(f"📄 {len(docs)} documents fetched from vector DB (search)")
        return docs

    # def keyword_search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
    #     """
    #             Perform a keyword search on the 'content' column.
    #
    #             Args:
    #                 query (str): The search query.
    #                 limit (int): Maximum number of results to return.
    #                 filters (Optional[Dict[str, Any]]): Filters to apply to the search.
    #
    #             Returns:
    #                 List[Document]: List of matching documents.
    #             """
    #     try:
    #         # Set default limit and filters if not provided
    #         limit = self.default_limit
    #         filters = self.filters_args or None
    #
    #         # Define the columns to select
    #         columns = [
    #             self.table.c.id,
    #             self.table.c.name,
    #             self.table.c.meta_data,
    #             self.table.c.content,
    #             self.table.c.embedding,
    #             self.table.c.usage,
    #             self.table.c.created_at,
    #         ]
    #
    #         # Build the base statement
    #         stmt = select(*columns)
    #
    #         # Build the text search vector
    #         ts_vector = func.to_tsvector(self.content_language, self.table.c.content)
    #         # Create the ts_query using websearch_to_tsquery with parameter binding
    #         processed_query = self.enable_prefix_matching(query) if self.prefix_match else query
    #         ts_query = func.websearch_to_tsquery(self.content_language, bindparam("query", value=processed_query))
    #         # Compute the text rank
    #         text_rank = func.ts_rank_cd(ts_vector, ts_query)
    #
    #         # Apply filters if provided
    #         if filters is not None:
    #             # Use the contains() method for JSONB columns to check if the filters column contains the specified filters
    #             stmt = stmt.where(self.table.c.filters.contains(filters))
    #
    #         # order by relevance rank + recency
    #         stmt = stmt.order_by(text_rank.desc(), self.table.c.created_at.desc())
    #
    #         # Limit the number of results
    #         stmt = stmt.limit(limit)
    #
    #         # Log the query for debugging
    #         logger.debug(f"Keyword search query: {stmt}")
    #
    #         # Execute the query
    #         try:
    #             with self.Session() as sess, sess.begin():
    #                 results = sess.execute(stmt).fetchall()
    #         except Exception as e:
    #             logger.error(f"Error performing keyword search: {e}")
    #             logger.error("Table might not exist, creating for future use")
    #             self.create()
    #             return []
    #
    #         # Process the results and convert to Document objects
    #         search_results: List[Document] = []
    #         for result in results:
    #             search_results.append(
    #                 Document(
    #                     id=result.id,
    #                     name=result.name,
    #                     meta_data=result.meta_data,
    #                     content=result.content,
    #                     embedder=self.embedder,
    #                     embedding=result.embedding,
    #                     usage=result.usage,
    #                 )
    #             )
    #
    #         return search_results
    #     except Exception as e:
    #         logger.error(f"Error in overridden keyword_search: {e}")
    #         return []

    def upsert(
            self,
            documents: List[Document],
            filters: Optional[Dict[str, Any]] = None,
            batch_size: int = 100,
    ) -> None:
        """
        Upsert (insert or update) documents in the database.

        Args:
            documents (List[Document]): List of documents to upsert.
            filters (Optional[Dict[str, Any]]): Filters to apply to the documents.
            batch_size (int): Number of documents to upsert in each batch.
        """
        try:
            with self.Session() as sess:
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i: i + batch_size]
                    logger.debug(f"Processing batch starting at index {i}, size: {len(batch_docs)}")
                    try:
                        # Prepare documents for upserting
                        batch_records = []
                        for doc in batch_docs:
                            try:
                                doc.embed(embedder=self.embedder)
                                cleaned_content = self._clean_content(doc.content)
                                content_hash = md5(cleaned_content.encode()).hexdigest()
                                _id = doc.id or content_hash
                                record = {
                                    "id": _id,
                                    "name": doc.name,
                                    "meta_data": doc.meta_data,
                                    "filters": filters,
                                    "content": cleaned_content,
                                    "embedding": doc.embedding,
                                    "usage": doc.usage,
                                    "content_hash": content_hash,
                                    "created_at": datetime.now(timezone.utc),
                                }
                                batch_records.append(record)
                            except Exception as e:
                                logger.error(f"Error processing document '{doc.name}': {e}")

                        # Upsert the batch of records
                        insert_stmt = postgresql.insert(self.table).values(batch_records)
                        upsert_stmt = insert_stmt.on_conflict_do_update(
                            index_elements=["id"],
                            set_=dict(
                                name=insert_stmt.excluded.name,
                                meta_data=insert_stmt.excluded.meta_data,
                                filters=insert_stmt.excluded.filters,
                                content=insert_stmt.excluded.content,
                                embedding=insert_stmt.excluded.embedding,
                                usage=insert_stmt.excluded.usage,
                                content_hash=insert_stmt.excluded.content_hash,
                                created_at=datetime.now(timezone.utc),
                            ),
                        )
                        sess.execute(upsert_stmt)
                        sess.commit()  # Commit batch independently
                        logger.info(f"Upserted batch of {len(batch_records)} documents.")
                    except Exception as e:
                        logger.error(f"Error with batch starting at index {i}: {e}")
                        sess.rollback()  # Rollback the current batch if there's an error
                        raise
        except Exception as e:
            logger.error(f"Error upserting documents: {e}")
            raise
