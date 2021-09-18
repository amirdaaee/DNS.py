from abc import abstractmethod

import dns.message

import DNS.Config


class Dict2Obj(object):
    def __init__(self, dictionary):
        for key in dictionary:
            setattr(self, key, dictionary[key])


class BasePlugin:
    CONFIG = {}
    _config = None

    def __init__(self, plugins, *args, **kwargs):
        type(plugins)
        pass

    # noinspection PyUnusedLocal
    @abstractmethod
    def before_resolve(self, query: dns.message.QueryMessage, response: dns.message.QueryMessage, address):
        return query, response

    # noinspection PyUnusedLocal
    @abstractmethod
    def after_resolve(self, query: dns.message.QueryMessage, response: dns.message.QueryMessage, address):
        return query, response

    @property
    def settings(self):
        return DNS.Config.Settings

    @property
    def config(self):
        if self._config:
            return self._config

        module_ = self.__class__.__module__.split('.')[1]
        class_ = module_ + '.' + self.__class__.__name__
        module_pref = 'Plugin__' + module_ + '__'
        class_pref = 'Plugin__' + class_ + '__'
        conf_module = {x.replace(module_pref, ''): y for x, y in self.settings if x.startswith(module_pref)}
        conf_class = {x.replace(class_pref, ''): y for x, y in self.settings if x.startswith(class_pref)}
        conf_ = {**conf_module, **conf_class}
        conf = Dict2Obj(conf_)
        self._config = conf
        return conf
