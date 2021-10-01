import atexit
import importlib
import inspect
import json
import os.path
import pickle
import pkgutil
from ipaddress import IPv4Address
from os import environ
from typing import Optional, List

from pydantic import BaseSettings, conint, create_model, Field

from DNS.Logging import logger
from DNS.Logging import reload as relog
from Plugins.Base import BasePlugin

port_type = conint(ge=0, le=65353)


class _BaseSettingType(BaseSettings):
    local_ip: IPv4Address = Field(title='local ip to bind', default='127.0.0.1')
    local_port: port_type = Field(title='local port to bind', default='5053')
    upstream_ip: IPv4Address = Field(title='upstream DNS server ip', default='8.8.8.8')
    upstream_port: port_type = Field(title='upstream DNS server port', default=53)
    plugins: List[str] = Field(title='plugins to activate', default=[])

    class Config:
        env_prefix = 'DNSPY__'


class Configuration:
    RUNTIME_FILE = './.config.runtime'
    PLUGIN_PACKAGE = 'Plugins'

    @staticmethod
    def global_config(config):
        type(config)
        relog()

    @classmethod
    def get_all_plugins(cls):
        def _plugin_check(obj):
            if inspect.isclass(obj):
                if issubclass(obj, BasePlugin):
                    return True
            return False

        def _plugin_name_check(name):
            return name != 'BasePlugin' and not name.startswith('_')

        plugin_modules = [name for _, name, _ in pkgutil.iter_modules([cls.PLUGIN_PACKAGE])]
        plugin_modules = [(module, importlib.import_module(f'{cls.PLUGIN_PACKAGE}.{module}')) for module in
                          plugin_modules]
        plugin_classes = {x[0]: [y for y in inspect.getmembers(x[1], _plugin_check) if _plugin_name_check(y[0])]
                          for x in plugin_modules}
        plugin_classes = {f'{k}.{v_[0]}': v_[1] for k, v in plugin_classes.items() for v_ in v}
        return plugin_classes

    @classmethod
    def _get_plugin_conf(cls, plugin: str):
        module, plug = plugin.split('.')
        plugin_module = importlib.import_module(f'{cls.PLUGIN_PACKAGE}.{module}')
        plugin_class = getattr(plugin_module, plug)
        conf_module = {f'Plugin__{module}__' + x: y for x, y in getattr(plugin_module, 'CONFIG', {}).items()}
        conf_plugin = {f'Plugin__{plugin}__' + x: y for x, y in getattr(plugin_class, 'CONFIG', {}).items()}
        conf = {**conf_module, **conf_plugin}

        return conf

    @classmethod
    def load(cls, active_all_plugins=False):
        plugins_all = cls.get_all_plugins()
        plugins_active_ = plugins_all if active_all_plugins else json.loads(environ.get('DNSPY__PLUGINS', '[]'))
        plugins_active = []
        for i_ in plugins_active_:
            if i_ not in plugins_all.keys():
                logger.warning(f'plugin {i_} not found. skipping...')
                continue
            plugins_active.append(i_)

        plugins_conf = {}
        for i_ in plugins_active:
            conf = cls._get_plugin_conf(i_)
            plugins_conf.update(conf)

        def _clean_exit():
            if os.path.isfile(cls.RUNTIME_FILE):
                os.remove(cls.RUNTIME_FILE)

        settings_model = create_model('settings_model', __base__=_BaseSettingType, **plugins_conf)
        data = settings_model(_env_file=None)
        data.plugins = plugins_active
        with open(cls.RUNTIME_FILE, 'wb') as f_:
            pickle.dump(data.dict(), f_)
        atexit.register(_clean_exit)
        global _settings
        _settings = data
        cls.global_config(data)
        return cls


def __getattr__(name):
    if name == 'Settings':
        global _settings
        if _settings is not None:
            logger.trace('reading configuration from cache')
            return _settings
        if os.path.isfile(Configuration.RUNTIME_FILE):
            logger.trace('reading configuration from runtime file')
            with open(Configuration.RUNTIME_FILE, 'rb') as f_:
                _settings = pickle.load(f_)
                return _settings
        else:
            logger.warning('configuration is not initiated yet')
            return None


_settings: Optional[_BaseSettingType] = None
Settings: Optional[_BaseSettingType]
