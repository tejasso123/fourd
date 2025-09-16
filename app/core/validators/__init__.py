from .ask_fouray_rules import ASK_FOURAY_RULES
from .file_upload_rules import FILE_UPLOAD_RULES
from .web_upload_rules import WEB_UPLOAD_RULES
from .base_validator import validate_request, validate_fields
from .user_create_rules import USER_CREATE_RULES
from .translate_rules import TRANSLATE_RULES

VALIDATION_RULES = {
    **ASK_FOURAY_RULES,
    **FILE_UPLOAD_RULES,
    **WEB_UPLOAD_RULES,
    **USER_CREATE_RULES,
    **TRANSLATE_RULES
}

__all__ = ["VALIDATION_RULES", "validate_request", "validate_fields", "FILE_UPLOAD_RULES",
           "WEB_UPLOAD_RULES", "ASK_FOURAY_RULES", "USER_CREATE_RULES", "TRANSLATE_RULES"]
