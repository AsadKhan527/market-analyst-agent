"""Central place tools are registered and dispatched. Add a new tool by adding
one entry here — the agent loop never needs to change."""
from app.tools.scrape import fetch_page, FETCH_TOOL_SCHEMA

TOOL_SCHEMAS = [FETCH_TOOL_SCHEMA]

_DISPATCH = {
    "fetch_page": lambda args: fetch_page(args["url"]),
}


def call_tool(name: str, arguments: dict) -> dict:
    if name not in _DISPATCH:
        return {"error": f"unknown tool: {name}"}
    try:
        result = _DISPATCH[name](arguments)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
