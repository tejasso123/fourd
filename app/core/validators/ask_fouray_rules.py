from typing import Dict, List

ASK_FOURAY_RULES: Dict[str, Dict[str, List[str]]] = {
    "product_description": {
        "required_fields": ["agent_id", "session_id", "product_sku"],
        "optional_fields": ["keywords", "further_details", "section_name", "streaming", "location", "language", "role",
                            "goal", "constraints", "previous_response", "custom_section"],
    },
    "legal_gv": {
        "required_fields": ["agent_id", "session_id", "parent_entity", "associate_enterprise", "niche"],
        "optional_fields": ["module_id", "user_input", "section_name", "streaming", "previous_response"],
    },
    "qa_auto_varseno": {
        "required_fields": ["agent_id", "session_id", "module_id"],
        "optional_fields": ["tags", "further_details", "streaming"],
    },
    "echo_insight": {
        "required_fields": ["agent_id", "session_id", "id"],
        "optional_fields": ["tags", "further_details", "streaming"],
    },
    "email": {
        "required_fields": ["agent_id", "session_id", "tone", "occasion", "template", "file"],
        "optional_fields": ["tags", "further_details", "streaming", "uid"],
    },
    "blog": {
        "required_fields": ["agent_id", "session_id", "step"],
        "optional_fields": ["further_details", "streaming", "blog_type", "seed_keywords", "blog_about",
                            "tone_of_voice", "blog_length", "location_focus", "language",
                            "semantic_clusters", "topic_map", "company_transcripts", "brand_context",
                            "image_guidelines", "uid", "section_name", "previous_response"],
    },
    "dosha_quiz": {
        "required_fields": ["agent_id", "session_id", "quiz_json", "streaming"],
        "optional_fields": [],
    },
    "free_form": {
        "required_fields": ["agent_id", "session_id", "streaming", "further_details", "language", "location_focus"],
        "optional_fields": ["role", "goal", "constraints", "uid", "image"],
    },
    "free_chat": {
        "required_fields": ["agent_id", "session_id", "streaming", "further_details"],
        "optional_fields": ["uid", "image_file"],
    },
}
