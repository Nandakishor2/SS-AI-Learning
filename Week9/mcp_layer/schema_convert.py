"""
MCP tool schema  ->  Gemini FunctionDeclaration.

This is the ONE piece of real glue that "automatic tool discovery" needs. An MCP server
advertises each tool's parameters as a JSON Schema (what `tools/list` returns). The agent
was hard-coded against hand-written `types.FunctionDeclaration`s in Week 7/8. Here we build
those declarations AT RUNTIME from whatever the server advertised — so the agent gains a
tool it never had source code for. Nothing about the agent's loop changes; only where its
tool list comes from.

Deliberately small and defensive: it handles the JSON-Schema subset fastmcp emits
(object / string / number / integer / boolean / array, `enum`, `description`, `required`,
nested `properties`, `items`) and ignores the rest rather than failing a whole tool.
"""
from google.genai import types

_TYPE_MAP = {
    "string": types.Type.STRING,
    "number": types.Type.NUMBER,
    "integer": types.Type.INTEGER,
    "boolean": types.Type.BOOLEAN,
    "object": types.Type.OBJECT,
    "array": types.Type.ARRAY,
}


def _json_type(node: dict) -> str:
    """Pick a usable JSON-Schema type, tolerating `["string","null"]` unions and $ref-less anyOf."""
    t = node.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    if t:
        return t
    for key in ("anyOf", "oneOf", "allOf"):
        for sub in node.get(key, []):
            if isinstance(sub, dict) and sub.get("type"):
                return _json_type(sub)
    return "string"  # safe default: an unknown param becomes a free-text string


def json_schema_to_gemini(node: dict) -> types.Schema:
    """Recursively convert one JSON-Schema node to a google-genai types.Schema."""
    node = node or {}
    jtype = _json_type(node)
    schema = types.Schema(type=_TYPE_MAP.get(jtype, types.Type.STRING))

    if node.get("description"):
        schema.description = node["description"]
    if node.get("enum"):
        schema.enum = [str(v) for v in node["enum"]]

    if jtype == "object":
        props = node.get("properties") or {}
        schema.properties = {k: json_schema_to_gemini(v) for k, v in props.items()}
        if node.get("required"):
            schema.required = list(node["required"])
    elif jtype == "array":
        schema.items = json_schema_to_gemini(node.get("items") or {})

    return schema


def tool_to_declaration(name: str, description: str, input_schema: dict) -> types.FunctionDeclaration:
    """Build a Gemini FunctionDeclaration from a discovered MCP tool."""
    params = json_schema_to_gemini(input_schema or {"type": "object", "properties": {}})
    return types.FunctionDeclaration(
        name=name,
        description=description or "",
        parameters=params,
    )
