"""Helper for extracting HA clients from FastMCP lifespan context."""


def get_clients(ctx) -> tuple:
    """Extract HA clients from the lifespan context.

    Returns (ws_client, rest_client) tuple.
    """
    ws = ctx.lifespan_context["ws"]
    rest = ctx.lifespan_context["rest"]
    return ws, rest
