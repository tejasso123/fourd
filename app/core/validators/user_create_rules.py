from typing import Dict, List

USER_CREATE_RULES: Dict[str, Dict[str, List[str]]] = {
    "user_creation": {
        "required_fields": ["email", "first_name", "last_name"],
        "optional_fields": [],
    }
}
