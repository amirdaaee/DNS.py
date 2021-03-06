from pydantic import Field

from DNS.Logging import logger
from Plugins.Base import BasePlugin

CONFIG = {
    'log_level': (str, Field(title='level of logs to write', default='info'))
}


class Log(BasePlugin):
    """
    log query data
    """
    CONFIG = {
        'question': (bool, Field(title='log question query', default=False)),
        'answer': (bool, Field(title='log answer query', default=True)),
    }

    @staticmethod
    def _query_message(query, address):
        message = f'query from {address}: '
        for q in query.question:
            message += f'{q.to_text()}\t'
        return message

    @staticmethod
    def _answer_message(answer, address):
        message = Log._query_message(answer, address)
        message += '| Answer: '
        for q in answer.answer:
            message += f'{q.to_text()}\t'
        return message

    def _log(self, message):
        getattr(logger, self.config.log_level)(message.replace('\n', '\\n'))

    def before_resolve(self, query, response, address, *args, **kwargs):
        if self.config.question:
            message = self._query_message(query, address)
            self._log(message)
        return query, response

    def after_resolve(self, query, response, address, *args, **kwargs):
        if self.config.answer:
            message = self._answer_message(response, address)
            self._log(message)
        return query, response
