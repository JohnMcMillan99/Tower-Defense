"""
DEPRECATED: Use utils.path_generator.PathGenerator instead.

This module is kept for backward compatibility only.
It will be removed in a future version.
"""
import warnings
from utils.path_generator import PathGenerator

warnings.warn(
    "TD3.PathGenerator is deprecated. Use utils.path_generator.PathGenerator instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["PathGenerator"]
