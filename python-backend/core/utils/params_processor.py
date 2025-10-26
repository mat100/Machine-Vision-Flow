"""
Parameter processing utilities.

Handles preparation and validation of detection parameters,
providing unified parameter handling across all detection methods.
"""

from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def prepare_params(params: Optional[T], params_class: Type[T]) -> T:
    """
    Prepare detection parameters with default initialization.

    If params is None, creates a new instance with defaults.
    If params is already an instance, returns it unchanged.

    Args:
        params: Parameters instance or None
        params_class: Pydantic parameter class for defaults

    Returns:
        Initialized parameters instance

    Example:
        >>> params = ParamsProcessor.prepare_params(
        ...     None, EdgeDetectionParams
        ... )
        >>> # Returns EdgeDetectionParams() with all defaults
    """
    if params is None:
        return params_class()
    return params


def params_to_dict(params: BaseModel, convert_enums: bool = True) -> Dict[str, Any]:
    """
    Convert Pydantic params to dictionary.

    Args:
        params: Pydantic parameter model instance
        convert_enums: Whether to convert enum values to strings

    Returns:
        Dictionary representation of parameters

    Example:
        >>> params = EdgeDetectionParams(method=EdgeMethod.CANNY)
        >>> data = ParamsProcessor.params_to_dict(params)
        >>> # Returns {"method": "canny", ...}
    """
    data = params.model_dump(exclude_none=True)

    if convert_enums:
        # Convert enum values to strings
        for key, value in data.items():
            if hasattr(value, "value"):
                data[key] = value.value

    return data


def extract_param(params: BaseModel, param_name: str, default: Any = None) -> Any:
    """
    Safely extract a parameter value from params object.

    Args:
        params: Parameters instance
        param_name: Name of parameter to extract
        default: Default value if parameter not found

    Returns:
        Parameter value or default

    Example:
        >>> method = ParamsProcessor.extract_param(
        ...     params, "method", EdgeMethod.CANNY
        ... )
    """
    return getattr(params, param_name, default)


def merge_params(base_params: Dict[str, Any], override_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two parameter dictionaries.

    Override params take precedence over base params.

    Args:
        base_params: Base parameters dictionary
        override_params: Override parameters (takes precedence)

    Returns:
        Merged parameters dictionary

    Example:
        >>> base = {"threshold": 100, "method": "canny"}
        >>> override = {"threshold": 150}
        >>> result = ParamsProcessor.merge_params(base, override)
        >>> # Returns {"threshold": 150, "method": "canny"}
    """
    result = base_params.copy()
    result.update(override_params)
    return result
