import click
import sys
import logging
from . import cli
from .params import project, db_options

from meltano.core.plugin_invoker import invoker_factory
from meltano.core.config_service import ConfigService
from meltano.core.tracking import GoogleAnalyticsTracker
from meltano.core.db import project_engine


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("plugin_name")
@click.argument("plugin_args", nargs=-1, type=click.UNPROCESSED)
@db_options
@project
def invoke(project, plugin_name, plugin_args, engine_uri):
    _, Session = project_engine(project, engine_uri, default=True)
    session = Session()

    try:
        config_service = ConfigService(project)
        plugin = config_service.get_plugin(plugin_name)
        service = invoker_factory(session, project, plugin)
        handle = service.invoke(*plugin_args)

        exit_code = handle.wait()

        tracker = GoogleAnalyticsTracker(project)
        tracker.track_meltano_invoke(
            plugin_name=plugin_name, plugin_args=" ".join(plugin_args)
        )

        sys.exit(exit_code)
    except Exception as err:
        logging.exception(err)
        click.secho(f"An error occured: {err}.", fg="red")
        raise click.Abort() from err
    finally:
        session.close()
