"""Helper for extracting HA clients from FastMCP lifespan context."""


def get_clients(ctx) -> tuple:
    """Extract HA clients from the lifespan context.

    Returns (ws_client, rest_client) tuple.
    """
    lifespan_result = ctx.fastmcp._lifespan_result
    ws = lifespan_result["ws"]
    rest = lifespan_result["rest"]
    return ws, rest
