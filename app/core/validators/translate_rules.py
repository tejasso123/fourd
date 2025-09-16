from typing import Dict, List

TRANSLATE_RULES: Dict[str, Dict[str, List[str]]] = {
    "language_translate": {
        "required_fields": ["json_data"],
        "optional_fields": ["source_language", "target_language", "target_region", "tone"]
    }
}
