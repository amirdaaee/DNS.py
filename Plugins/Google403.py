import asyncio
from typing import Optional

import aiohttp
import dns.rdatatype
from aiohttp.client_exceptions import ClientError, ServerTimeoutError
from pydantic import Field
from pydantic import RedisDsn

from DNS.Logging import logger
from Plugins import Authoritative
from Plugins.Authoritative import _Authoritative

# todo: cname response support [for A type request]

CONFIG = {
    'redis_uri': (Optional[RedisDsn],
                  Field(title='redis server uri. if None, will use Authoritative plugin redis_uri', default=None))
}


class Inquirer(_Authoritative):
    """
    resolve auto-detected google403 blocked domains with sni proxy IP
    this plugin must be used in conjunction with plugin Authoritative.BlackList and that must be defined before
    this plugin.
    Authoritative.BlackList response_ip should be set to SNI proxy ip
    """
    CONFIG = {
        'redis_key_que': (
            str,
            Field(title='key to read/write Inquiring que in redis server [set]', default='G403_que')
        ),
        'redis_key_open': (
            str,
            Field(title='key to read/write open domains in redis server [set]', default='G403_open')
        ),
        'redis_key_block': (
            str,
            Field(title='key to read/write blocked domains in redis server [set]', default='G403_block')
        ),
        'redis_key_unknown': (
            str,
            Field(title='key to read/write domains with unknown state in redis server [set]', default='G403_unknown')
        )
    }

    def __init__(self, plugins, *args, **kwargs):
        resolver = None
        for p_ in plugins:
            if isinstance(p_, Authoritative.BlackList):
                resolver: Optional[Authoritative.BlackList] = p_
                break
        try:
            assert resolver
        except AssertionError as e:
            logger.critical(
                "Plugin Google403.Inquirer must be used in conjunction with plugin Authoritative.BlackList "
                "and that must be defined before Google403.Inquirer plugin and response_ip should be set "
                "to SNI proxy ip"
            )
            raise e
        if self.config.redis_uri is None:
            self._config.redis_uri = resolver.config.redis_uri
        super(Inquirer, self).__init__(plugins, *args, **kwargs)
        self.resolver = resolver
        self.resolver_key = resolver.config.redis_key_A
        asyncio.get_event_loop().run_until_complete(self._init_db())
        asyncio.get_event_loop().create_task(self._init_inquirer())

    async def add_domains(self, *domains):
        domains = [x.replace('www.', '', 1) if x.startswith('www.') else x for x in domains]
        subdomains = ['*.' + x for x in domains]
        await self.resolver.redis.sadd(self.resolver_key, *[*domains, *subdomains])

    async def _init_db(self):
        members = await self.redis.smembers(self.config.redis_key_block)
        if members:
            await self.add_domains(*members)
            logger.info(f'added {len(members)} domain to {self.resolver_key}')
        return

    async def _init_inquirer(self):
        # todo: run in parallel loop
        # todo: add redis ttl for unknown hosts
        while True:
            query = await self.redis.spop(self.config.redis_key_que)
            if query:
                logger.info(f'got {query} to inquire')
                asyncio.create_task(self.inquire(query))
            else:
                logger.trace(f'no query to inquire')
                await asyncio.sleep(1)

    async def inquire(self, host):
        mode = await self.is_blocked(host)
        add2resolver = False
        if mode == 'o':
            key = self.config.redis_key_open
        elif mode == 'b':
            key = self.config.redis_key_block
            add2resolver = True
        else:
            key = self.config.redis_key_unknown
        await self.redis.sadd(key, host)
        if add2resolver:
            await self.add_domains(host)
            logger.info(f'added {host} to {self.resolver_key}')

    @staticmethod
    async def is_blocked(host):

        inspect_msg = 'Your client does not have permission to get URL'
        timeout = aiohttp.ClientTimeout(sock_read=60)
        # noinspection HttpUrlsUsage
        for schema in ['https://', 'http://']:
            url = schema + host
            try:
                logger.info(f'checking {url} for google 403')
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        logger.debug(f'{url} responded with code {resp.status}')
                        if resp.status == 403 and inspect_msg in await resp.text():
                            logger.info(f'{url} is blocked')
                            return 'b'
                        logger.info(f'{url} is open')
                        return 'o'
            except (ClientError, ServerTimeoutError) as e:
                logger.error(f'error getting {url} [{e}]')
        return 'u'

    async def before_resolve(self, query, response, *args, **kwargs):
        for q_ in query.question:
            if q_.rdtype == dns.rdatatype.A:
                name = q_.name.to_text(True)
                for i_ in [self.config.redis_key_open, self.config.redis_key_block,
                           self.config.redis_key_unknown]:
                    state = await self.redis.sismember(i_, name)
                    if state:
                        logger.info(f'found record for {name} in {i_}')
                        break
                if state:
                    continue
                logger.info(f'no record for {name}. adding to {self.config.redis_key_que}')
                await self.redis.sadd(self.config.redis_key_que, name)
        return query, response

    async def after_resolve(self, query, response, *args, **kwargs):
        return query, response
