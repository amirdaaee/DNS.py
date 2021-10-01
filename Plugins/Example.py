from pydantic import Field

from Plugins.Base import BasePlugin

CONFIG = {
    'message_before_module_level': (str,
                                    Field(title='message to print before upstream resolve', default='hello world')),
    'message_after_module_level': (str, Field(title='message to print after upstream resolve', default='goodbye world'))
}


class ExamplePlugin(BasePlugin):
    """
    print message before and after upstream resolve
    """
    CONFIG = {
        'message_before': (str, Field(title='message to print before upstream resolve', default='hello dns')),
        'message_after': (str, Field(title='message to print after upstream resolve', default='goodbye dns')),
    }

    def before_resolve(self, query, response, *args, **kwargs):
        print('Pre Resolve Plugin example [module level]:', self.config.message_before_module_level)
        print('Pre Resolve Plugin example [class level]:', self.config.message_before)
        return query, response

    def after_resolve(self, query, response, *args, **kwargs):
        print('post Resolve Plugin example [module level]:', self.config.message_after_module_level)
        print('post Resolve Plugin example [class level]:', self.config.message_after)
        return query, response
