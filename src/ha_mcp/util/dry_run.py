import logging
import yaml
from fastmcp import Context

logger = logging.getLogger(__name__)

async def confirm_change(
    ctx: Context,
    action: str,
    entity_type: str,
    identifier: str,
    config: dict,
    validation_result: dict | None = None,
    skip_confirm: bool = False,
) -> bool:
    """Show YAML preview and ask for confirmation before applying changes.

    Args:
        ctx: FastMCP context
        action: Action being performed (CREATE, UPDATE, DELETE)
        entity_type: Type of entity (automation, script, scene, etc.)
        identifier: Entity identifier
        config: Configuration to preview
        validation_result: Optional validation results to include
        skip_confirm: Skip confirmation (for clients without elicitation)

    Returns:
        True if confirmed, False if cancelled.
    """
    if skip_confirm:
        logger.info("Skipping confirmation for %s %s: %s", action, entity_type, identifier)
        return True

    yaml_preview = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)

    message_parts = [
        f"## {action.upper()} {entity_type}: {identifier}",
        "",
        "```yaml",
        yaml_preview.rstrip(),
        "```",
    ]

    if validation_result:
        valid = validation_result.get("valid", True)
        errors = validation_result.get("errors", [])
        warnings = validation_result.get("warnings", [])

        message_parts.append("")
        message_parts.append(f"### Validation: {'PASSED' if valid else 'FAILED'}")

        if errors:
            message_parts.append("**Errors:**")
            for err in errors:
                message_parts.append(f"- {err}")

        if warnings:
            message_parts.append("**Warnings:**")
            for warn in warnings:
                message_parts.append(f"- {warn}")

        if not valid:
            message_parts.append("")
            message_parts.append("**Validation failed. Cannot apply.**")
            return False

    message_parts.append("")
    message_parts.append("Apply this change?")

    message = "\n".join(message_parts)

    try:
        response = await ctx.elicit(
            message=message,
            response_type=["confirm", "cancel"]
        )
        confirmed = response.action == "accept" and response.data == "confirm"
    except Exception as e:
        # If elicitation is not supported, log and return based on skip_confirm_default
        logger.warning("Elicitation not supported by client: %s. Proceeding with default.", e)
        from ha_mcp.config import settings
        confirmed = settings.skip_confirm_default

    if confirmed:
        logger.info("User confirmed %s %s: %s", action, entity_type, identifier)
    else:
        logger.info("User cancelled %s %s: %s", action, entity_type, identifier)

    return confirmed
