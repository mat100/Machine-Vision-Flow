"""
Utility modules for core functionality - functional architecture.

This package contains reusable utility functions for domain-agnostic operations.

Modules:
- camera_identifier: Parse camera ID strings
- coordinate_adjuster: ROI coordinate adjustment
- decorators: Utility decorators (timer, etc.)
- enum_converter: Enum parsing and conversion
- params_processor: Parameter processing utilities
"""

# Camera identifier functions
from .camera_identifier import TYPE_IP, TYPE_TEST, TYPE_USB, format, parse

# Coordinate adjuster functions
from .coordinate_adjuster import adjust_for_roi_offset, extract_roi_offset

# Decorators
from .decorators import timer

# Enum converter functions
from .enum_converter import enum_to_string, parse_enum

# Params processor functions
from .params_processor import extract_param, merge_params, params_to_dict, prepare_params

__all__ = [
    # Camera identifier
    "parse",
    "format",
    "TYPE_USB",
    "TYPE_TEST",
    "TYPE_IP",
    # Coordinate adjuster
    "adjust_for_roi_offset",
    "extract_roi_offset",
    # Decorators
    "timer",
    # Enum converter
    "parse_enum",
    "enum_to_string",
    # Params processor
    "prepare_params",
    "params_to_dict",
    "extract_param",
    "merge_params",
]
