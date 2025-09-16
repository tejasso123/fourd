from typing import Dict, List

FILE_UPLOAD_RULES: Dict[str, Dict[str, List[str]]] = {
    "product_description": {
        "required_fields": ["sku"],
        "optional_fields": ["tags"],
    },
    "legal_gv": {
        "required_fields": [],
        "optional_fields": ["module_id", "tags"],
    },
    "qa_auto_varseno": {
        "required_fields": ["module_id"],
        "optional_fields": ["tags"],
    },
    "echo_insight": {
        "required_fields": ["id"],
        "optional_fields": ["tags"],
    },
    "email": {
        "required_fields": [],
        "optional_fields": ["tags", "template", "uid"],
    },
    "blog": {
        "required_fields": [],
        "optional_fields": ["tags", "documents", "uid"],
    },
    "free_chat": {
        "required_fields": [],
        "optional_fields": ["tags", "documents", "uid"],
    }
}
