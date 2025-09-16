from typing import Optional, Dict, Any
import json

from phi.agent import Agent
from phi.document import Document


class LegalGVAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.previous_response: Optional[str] = None

    def add_to_knowledge(self, section_name: str, result: str) -> str:
        """Use this function to add information to the knowledge base for future use.

        Args:
            section_name: The query to add.
            result: The result of the query.

        Returns:
            str: A string indicating the status of the addition.
        """
        if self.knowledge is None:
            return "Knowledge base not available"
        document_name = self.name
        if document_name is None:
            document_name = section_name.replace(" ", "_").replace("?", "").replace("!", "").replace(".", "")
        # document_content = json.dumps({"query": query, "result": result})
        document_content = json.dumps(
            {"section_name": section_name, "previous_response": self.previous_response, "user_feedback": result})
        print(f"Adding document to knowledge base: {document_name}: {document_content}")
        self.knowledge.load_document(
            document=Document(
                name=document_name,
                content=document_content,
                meta_data={"source": "user_feedback", "name": document_name},
            ),
            upsert=True,
            filters={"custom_tag": "feedback", "match": "exact"},
        )
        return "Successfully added to knowledge base"
