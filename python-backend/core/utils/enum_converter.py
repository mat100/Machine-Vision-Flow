"""
Enum conversion utilities.

Provides standardized methods for converting between enums and strings,
with support for case-insensitive parsing and fallback defaults.
"""

from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar("T")


def parse_enum(value: Any, enum_class: Type[T], default: T, normalize: bool = False) -> T:
    """
    Parse value to enum with fallback to default.

    Unifies enum parsing logic across all detection methods.

    Args:
        value: Value to parse (string, enum, or None)
        enum_class: Enum class to parse to
        default: Default enum value if parsing fails
        normalize: Whether to lowercase string before parsing
            (for case-insensitive matching)

    Returns:
        Parsed enum value or default

    Example:
        >>> method = EnumConverter.parse_enum(
        ...     "CANNY", EdgeMethod, EdgeMethod.CANNY, normalize=True
        ... )
        >>> # Returns EdgeMethod.CANNY for "canny", "Canny", "CANNY"
    """
    # Already an enum instance
    if isinstance(value, enum_class):
        return value

    # None or missing value
    if value is None:
        return default

    # String value - try to parse
    try:
        str_value = value.lower() if normalize else value
        return enum_class(str_value)
    except (ValueError, AttributeError):
        return default


def enum_to_string(value: Any) -> str:
    """
    Convert enum to string value, or pass through if already string.

    Unifies enum → string conversion across all detection methods.

    Args:
        value: Enum instance or string

    Returns:
        String value (enum.value if enum, otherwise the value itself)

    Example:
        >>> dictionary_str = EnumConverter.enum_to_string(ArucoDict.DICT_4X4_50)
        >>> # Returns "DICT_4X4_50"
    """
    return value.value if hasattr(value, "value") else value


def ensure_dict(params: Optional[Dict]) -> Dict:
    """
    Ensure params is a dict (create empty dict if None).

    Unifies params initialization across all detection methods.

    Args:
        params: Parameters dict or None

    Returns:
        Dict (original or empty if None)

    Example:
        >>> params = EnumConverter.ensure_dict(None)
        >>> # Returns {}
        >>> params = EnumConverter.ensure_dict({"key": "value"})
        >>> # Returns {"key": "value"}
    """
    return params if params is not None else {}


def convert_enums_to_strings(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert all enum values in a dictionary to strings.

    Useful for preparing parameters for functions that expect string values.

    Args:
        data: Dictionary potentially containing enum values

    Returns:
        New dictionary with all enums converted to strings

    Example:
        >>> data = {"method": EdgeMethod.CANNY, "threshold": 100}
        >>> result = EnumConverter.convert_enums_to_strings(data)
        >>> # Returns {"method": "canny", "threshold": 100}
    """
    result = {}
    for key, value in data.items():
        if hasattr(value, "value"):
            result[key] = value.value
        else:
            result[key] = value
    return result
