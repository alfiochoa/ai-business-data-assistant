"""Exceptions raised by the controlled business tool layer.

Tool functions must never leak raw database driver exceptions (e.g. a raw
psycopg2 traceback) up to the LLM orchestration layer or the API — wrap them
here instead.
"""


class ToolValidationError(ValueError):
    """A tool was called with invalid, out-of-range, or disallowed parameters."""


class ToolExecutionError(RuntimeError):
    """A tool's underlying query/database call failed."""
