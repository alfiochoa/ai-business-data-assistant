"""Verify the OpenAI tool schemas are well-formed and stay in sync with the
actual business-tool registry. No network/API calls."""

from __future__ import annotations

import inspect

from app.llm.schemas import TOOL_NAMES, TOOL_SCHEMAS
from app.tools.registry import TOOL_REGISTRY

REQUIRED_TOP_LEVEL_KEYS = {"type", "function"}
REQUIRED_FUNCTION_KEYS = {"name", "description", "parameters"}


def test_every_schema_has_required_shape():
    for schema in TOOL_SCHEMAS:
        assert REQUIRED_TOP_LEVEL_KEYS.issubset(schema.keys())
        assert schema["type"] == "function"
        function = schema["function"]
        assert REQUIRED_FUNCTION_KEYS.issubset(function.keys())
        assert isinstance(function["description"], str) and function["description"].strip()
        params = function["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        for required_param in params.get("required", []):
            assert required_param in params["properties"]


def test_schema_names_match_tool_registry_exactly():
    assert TOOL_NAMES == set(TOOL_REGISTRY.keys())


def test_schema_required_params_match_function_signature_required_args():
    for schema in TOOL_SCHEMAS:
        name = schema["function"]["name"]
        func = TOOL_REGISTRY[name]
        sig = inspect.signature(func)
        required_python_params = {
            p.name
            for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
        }
        schema_required = set(schema["function"]["parameters"].get("required", []))
        assert schema_required == required_python_params, (
            f"{name}: schema requires {schema_required}, "
            f"function requires {required_python_params}"
        )
