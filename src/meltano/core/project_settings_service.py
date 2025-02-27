"""Project Settings Service."""

from typing import List

from dotenv import dotenv_values

from meltano.core.setting_definition import SettingDefinition
from meltano.core.settings_service import (
    FeatureFlags,
    SettingsService,
    SettingValueStore,
)
from meltano.core.utils import expand_env_vars as do_expand_env_vars
from meltano.core.utils import nest_object

from .config_service import ConfigService

UI_CFG_SETTINGS = {
    "ui.server_name": "SERVER_NAME",
    "ui.secret_key": "SECRET_KEY",
    "ui.password_salt": "SECURITY_PASSWORD_SALT",
}


class ProjectSettingsService(SettingsService):
    """Project Settings Service."""

    config_override = {}

    def __init__(self, *args, config_service: ConfigService = None, **kwargs):
        """Instantiate ProjectSettingsService instance.

        Args:
            args: Positional arguments to pass to the superclass.
            config_service: Project configuration service instance.
            kwargs: Keyword arguments to pass to the superclass.
        """
        super().__init__(*args, **kwargs)

        self.config_service = config_service or ConfigService(self.project)

        self.env_override = {**self.project.env, **self.env_override}

        if self.project.active_environment:
            # Update this with `self.project.dotenv_env`, `self.env`, etc. to expand
            # other environment variables in the Environment's `env`.
            expandable_env = {**self.project.env}
            with self.feature_flag(
                FeatureFlags.STRICT_ENV_VAR_MODE, raise_error=False
            ) as strict_env_var_mode:
                environment_env = {
                    var: do_expand_env_vars(
                        value, expandable_env, raise_if_missing=strict_env_var_mode
                    )
                    for var, value in self.project.active_environment.env.items()
                }
            self.env_override.update(environment_env)

        self.config_override = {  # noqa: WPS601
            **self.__class__.config_override,
            **self.config_override,
        }

    @property
    def label(self) -> str:
        """Return label.

        Returns:
            Project label.
        """
        return "Meltano"

    @property
    def docs_url(self) -> str:
        """Return docs URL.

        Returns:
            URL for Meltano doc site.
        """
        return "https://docs.meltano.com/reference/settings"

    @property
    def env_prefixes(self) -> List[str]:
        """Return prefixes for setting environment variables.

        Returns:
            A list of project ENV VAR prefix strings.
        """
        return ["meltano"]

    @property
    def db_namespace(self) -> str:
        """Return namespace for setting value records in system database.

        Returns:
            Namespace for setting value records in system database.
        """
        return "meltano"

    @property
    def setting_definitions(self) -> List[SettingDefinition]:
        """Return definitions of supported settings.

        Returns:
            A list of defined settings.
        """
        return self.config_service.settings

    @property
    def meltano_yml_config(self):
        """Return current configuration in `meltano.yml`.

        Returns:
            Current configuration in `meltano.yml`.
        """
        return self.config_service.current_config

    @property
    def environment_config(self):
        """Return current environment configuration in `meltano.yml`.

        Returns:
            Current environment configuration in `meltano.yml`
        """
        return self.config_service.current_environment_config

    def update_meltano_yml_config(self, config):
        """Update configuration in `meltano.yml`.

        Args:
            config: Updated config.
        """
        self.config_service.update_config(config)

    def update_meltano_environment_config(self, config: dict):
        """Update environment configuration in `meltano.yml`.

        Args:
            config: Updated environment config.
        """
        self.config_service.update_environment_config(config)

    def process_config(self, config) -> dict:
        """Process configuration dictionary for presentation in `meltano config meltano`.

        Args:
            config: Config to process.

        Returns:
            Processed configuration dictionary for presentation in `meltano config meltano`.
        """
        return nest_object(config)

    def get_with_metadata(self, name: str, *args, **kwargs):
        """Return setting value with metadata.

        Args:
            name: Name of setting to get.
            args: Positional arguments to pass to the superclass method.
            kwargs: Keyword arguments to pass to the superclass method.

        Returns:
            Setting value with metadata.
        """
        value, metadata = super().get_with_metadata(name, *args, **kwargs)
        source = metadata["source"]

        if source is SettingValueStore.DEFAULT:
            # Support legacy `ui.cfg` files generated by `meltano ui setup`
            ui_cfg_value = self.get_from_ui_cfg(name)
            if ui_cfg_value is not None:
                value = ui_cfg_value
                metadata["source"] = SettingValueStore.ENV
        return value, metadata

    def get_from_ui_cfg(self, name: str):
        """Return setting value from UI config.

        Args:
            name: Name of setting to get.

        Returns:
            Setting value from UI config.
        """
        try:
            key = UI_CFG_SETTINGS[name]
            config = dotenv_values(self.project.root_dir("ui.cfg"))
            value = config[key]

            # Since `ui.cfg` is technically a Python file, `'None'` means `None`
            if value == "None":
                value = None

            return value
        except KeyError:
            return None
