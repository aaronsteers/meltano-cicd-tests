"""Tracking plugin context for the Snowplow tracker."""
from __future__ import annotations

import uuid

from snowplow_tracker import SelfDescribingJson
from structlog.stdlib import get_logger

from meltano.core.plugin.project_plugin import ProjectPlugin
from meltano.core.utils import hash_sha256, safe_hasattr

logger = get_logger(__name__)

PLUGINS_CONTEXT_SCHEMA = "iglu:com.meltano/plugins_context/jsonschema"
PLUGINS_CONTEXT_SCHEMA_VERSION = "1-0-0"


def _from_plugin(plugin: ProjectPlugin, cmd: str) -> dict:
    if not safe_hasattr(plugin, "info"):
        logger.debug(
            "Plugin tracker context some how encountered plugin without into attr."
        )
        # don't try to snag any info for this plugin, we're somehow badly malformed (unittest?)
        return {}

    return {
        "category": str(plugin.type),
        "name_hash": hash_sha256(plugin.name) if plugin.name else None,
        "variant_name_hash": hash_sha256(plugin.variant) if plugin.variant else None,
        "pip_url_hash": hash_sha256(plugin.formatted_pip_url)
        if plugin.formatted_pip_url
        else None,
        "parent_name_hash": hash_sha256(plugin.parent.name)
        if plugin.parent.name
        else None,
        "command": cmd,
    }


# Proactively named to avoid name collisions more widely used "PluginContext"
class PluginsTrackingContext(SelfDescribingJson):
    """Tracking context for the Meltano plugins."""

    def __init__(self, plugins: list(tuple[ProjectPlugin, str])):
        """Initialize a meltano tracking plugin context.

        Args:
            plugins: The Meltano plugins and the requested command.
        """
        tracking_context = []
        for plugin, cmd in plugins:
            tracking_context.append(_from_plugin(plugin, cmd))

        super().__init__(
            f"{PLUGINS_CONTEXT_SCHEMA}/{PLUGINS_CONTEXT_SCHEMA_VERSION}",
            {"context_uuid": str(uuid.uuid4()), "plugins": tracking_context},
        )

    def append_plugin_context(self, plugin: ProjectPlugin, cmd: str):
        """Append a plugin context to the tracking context.

        Args:
            plugin: The Meltano plugin.
            cmd: The command that was executed.
        """
        self["plugins"].append({_from_plugin(plugin, cmd)})
