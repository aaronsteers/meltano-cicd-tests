"""Plugin Add CLI."""

from typing import List

import click

from meltano.core.legacy_tracking import LegacyTracker
from meltano.core.plugin import PluginType
from meltano.core.plugin.base import PluginRef
from meltano.core.plugin.project_plugin import ProjectPlugin
from meltano.core.plugin_install_service import PluginInstallReason
from meltano.core.project import Project
from meltano.core.project_add_service import ProjectAddService
from meltano.core.project_plugins_service import ProjectPluginsService

from . import cli
from .params import pass_project
from .utils import (
    CliError,
    add_plugin,
    add_required_plugins,
    check_dependencies_met,
    install_plugins,
)


@cli.command(short_help="Add a plugin to your project.")
@click.argument("plugin_type", type=click.Choice(PluginType.cli_arguments()))
@click.argument("plugin_name", nargs=-1, required=True)
@click.option(
    "--inherit-from",
    help=(
        "Add a plugin inheriting from an existing plugin in the project"
        + " or a discoverable plugin identified, by name."
    ),
)
@click.option(
    "--variant",
    help="Add a specific (non-default) variant of the identified discoverable plugin.",
)
@click.option(
    "--as",
    "as_name",
    help=(
        "Shorthand for '--inherit-from', that can be used to add a discoverable "
        + "plugin to your project with a different name. "
        + "Usage:\b\n\nadd <type> <inherit-from> --as <name>"
    ),
)
@click.option(
    "--custom",
    is_flag=True,
    help="Add a custom plugin. The command will prompt you for the package's base plugin description metadata.",
)
@pass_project()
@click.pass_context
def add(
    ctx,
    project: Project,
    plugin_type: str,
    plugin_name: str,
    inherit_from: str = None,
    variant: str = None,
    as_name: str = None,
    **flags,
):
    """
    Add a plugin to your project.

    \b\nRead more at https://docs.meltano.com/reference/command-line-interface#add
    """
    plugin_type = PluginType.from_cli_argument(plugin_type)
    plugin_names = plugin_name  # nargs=-1

    if as_name:
        # `add <type> <inherit-from> --as <name>``
        # is equivalent to:
        # `add <type> <name> --inherit-from <inherit-from>``
        inherit_from = plugin_names[0]
        plugin_names = [as_name]

    plugins_service = ProjectPluginsService(project)

    if flags["custom"]:
        if plugin_type in {
            PluginType.TRANSFORMS,
            PluginType.ORCHESTRATORS,
        }:
            raise CliError(f"--custom is not supported for {plugin_type}")

    plugin_refs = [
        PluginRef(plugin_type=plugin_type, name=name) for name in plugin_names
    ]
    dependencies_met, err = check_dependencies_met(
        plugin_refs=plugin_refs, plugins_service=plugins_service
    )
    if not dependencies_met:
        raise CliError(f"Failed to install plugin(s): {err}")

    add_service = ProjectAddService(project, plugins_service=plugins_service)

    plugins: List[ProjectPlugin] = []
    tracker = LegacyTracker(project)
    for plugin in plugin_names:
        plugins.append(
            add_plugin(
                project,
                plugin_type,
                plugin,
                inherit_from=inherit_from,
                variant=variant,
                custom=flags["custom"],
                add_service=add_service,
            )
        )
        tracker.track_meltano_add(plugin_type=plugin_type, plugin_name=plugin)

        required_plugins = add_required_plugins(
            project, plugins, add_service=add_service
        )
    plugins.extend(required_plugins)

    success = install_plugins(project, plugins, reason=PluginInstallReason.ADD)

    if not success:
        raise CliError("Failed to install plugin(s)")

    _print_plugins(plugins)


def _print_plugins(plugins):
    printed_empty_line = False
    for plugin in plugins:
        docs_url = plugin.docs or plugin.repo
        if not docs_url:
            continue

        if not printed_empty_line:
            click.echo()
            printed_empty_line = True

        click.echo(
            f"To learn more about {plugin.type.descriptor} '{plugin.name}', visit {docs_url}"
        )
