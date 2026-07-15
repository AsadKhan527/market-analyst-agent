"""Central place tools are registered and dispatched. Add a new tool by adding
one entry here — the agent loop never needs to change."""
from app.tools.search import web_search, SEARCH_TOOL_SCHEMA
from app.tools.scrape import fetch_page, FETCH_TOOL_SCHEMA

TOOL_SCHEMAS = [SEARCH_TOOL_SCHEMA, FETCH_TOOL_SCHEMA]

_DISPATCH = {
    "web_search": lambda args: web_search(args["query"]),
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
