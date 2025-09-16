from typing import Dict, List

WEB_UPLOAD_RULES: Dict[str, Dict[str, List[str]]] = {
    "product_description_web_upload": {
        "required_fields": ["url", "sku"],
        "optional_fields": ["tags"],
    },
    "legal_gv": {
        "required_fields": ["url"],
        "optional_fields": ["module_id", "tags"],
    },
    "qa_auto_varseno": {
        "required_fields": ["url"],
        "optional_fields": ["tags"],
    },
    "echo_insight": {
        "required_fields": ["url"],
        "optional_fields": ["tags"],
    },
    "email": {
        "required_fields": ["url"],
        "optional_fields": ["tags", "template", "uid"],
    },
    "blog": {
        "required_fields": ["url"],
        "optional_fields": ["tags", "documents", "uid"],
    },
    "free_chat": {
        "required_fields": ["url"],
        "optional_fields": ["tags", "uid"],
    }
}
