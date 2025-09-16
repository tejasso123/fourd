from typing import Dict, List, Set, Tuple, Any
from app.core.exceptions import BadRequestException


def validate_fields(
        request_type: str,
        additional_data: Dict[str, Any],
        rules: Dict[str, List[str]]
) -> Tuple[List[str], List[str]]:
    """
    Core validation logic for checking required and optional fields.

    Args:
        request_type: The type of request
        additional_data: The data to validate
        rules: Dictionary with 'required_fields' and 'optional_fields'

    Returns:
        Tuple of (missing_fields, extra_fields)

    Raises:
        ValueError: If rules are malformed
    """
    required_fields: Set[str] = set(rules.get("required_fields", []))
    optional_fields: Set[str] = set(rules.get("optional_fields", []))
    allowed_fields: Set[str] = required_fields.union(optional_fields)

    provided_fields: Set[str] = set(additional_data.keys())

    missing_fields = [
        field for field in required_fields
        if field not in additional_data or additional_data[field] is None or additional_data[field] == ""
    ]
    extra_fields = [
        field for field in provided_fields
        if field not in allowed_fields
    ]

    return missing_fields, extra_fields


def validate_request(
        request_type: str,
        additional_data: Dict[str, Any],
        all_rules: Dict[str, Dict[str, List[str]]]
) -> Tuple[List[str], List[str]]:
    """
    Validate a request against provided rules.

    Args:
        request_type: The request type to validate
        additional_data: The data to validate
        all_rules: Complete set of validation rules

    Returns:
        Tuple of (missing_fields, extra_fields)

    Raises:
        ValueError: If request_type is invalid
    """
    if request_type not in all_rules:
        supported_types = ", ".join(all_rules.keys())
        raise BadRequestException(f"Invalid request_type. Supported types: {supported_types}")

    return validate_fields(request_type, additional_data, all_rules[request_type])
