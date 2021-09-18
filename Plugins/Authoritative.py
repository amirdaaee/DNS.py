import copy
from abc import abstractmethod
from ipaddress import IPv4Address
from typing import Optional, List

import aioredis
import dns.message
import dns.rdtypes.ANY.CNAME
import dns.rdtypes.IN.A
import dns.rrset
from pydantic import RedisDsn

import DNS.Config
import DNS.Utilities
from DNS.Logging import logger
from Plugins.Base import BasePlugin

# todo: add more dns question types support [AAAA,CNAME,NS,PTR,SOA,...]
# todo: cname response support [for A type request]

CONFIG = {
    'redis_uri': (RedisDsn, ...),
    'default_ttl': (int, 0)
}


class _Authoritative(BasePlugin):
    def _init_redis(self, redis=None):
        return redis or aioredis.from_url(self.config.redis_uri, encoding="utf-8", decode_responses=True)

    def __init__(self, *args, **kwargs):
        super(_Authoritative, self).__init__(*args, **kwargs)
        self.redis = self._init_redis(kwargs.get('redis', None))

    async def redis_iterative_lookup(self, key, name, func):
        def _function(x):
            return getattr(self.redis, func)(key, x)

        logger.info(f'iterative lookup for {name} in {key} using {func} in redis')
        result = await DNS.Utilities.async_iterative_lookup(name, _function)
        return result

    @staticmethod
    def _manual_answer(questions, q, answers, a):
        questions.remove(q)
        answers.append(a)

    @abstractmethod
    async def before_resolve(self, query, response, *args, **kwargs):
        return query, response

    @abstractmethod
    async def after_resolve(self, query, response, *args, **kwargs):
        return query, response


class LocalDB(_Authoritative):
    # todo: ttl assignment in db record
    """
    queries domain name from redis DB and response respectively. doesn't touch anything if answer not in local DB
    notes:
        - currently just supports "A" type question and response
        - domains should be stored in db without trailing dot
        - multiple ips for domain can be set using ";" delimiter
        - subdomain wildcard is supported (e.g. *.google.com)
    """

    CONFIG = {
        'redis_key_A': (str, 'LocalDB'),
    }

    async def before_resolve(self, query, response, *args, **kwargs):
        ttl = self.config.default_ttl
        redis_key = self.config.redis_key_A
        for q_ in query.question:
            if q_.rdtype == dns.rdatatype.A:
                name = q_.name
                result = await self.redis_iterative_lookup(redis_key, name, 'hget')
                if result:
                    logger.info(f'found local record for {q_.to_text()} : {result}')
                    r_ = DNS.Utilities.create_rrset(dns.rdatatype.A, q_.name, addresses=result.split(';'), ttl=ttl)
                    self._manual_answer(query.question, q_, response.answer, r_)
        return query, response

    async def after_resolve(self, query, response, *args, **kwargs):
        return query, response


class BlackList(_Authoritative):
    """
    doesn't touch any questions except some hosts defined in redis db which will resolve to predefined ip
    notes:
        - currently just supports "A" type question and response
        - domains should be stored in db without trailing dot
        - subdomain wildcard is supported (e.g. *.google.com)
    """

    CONFIG = {
        'redis_key_A': (str, 'BLDB'),
        'response_ip': (List[IPv4Address], ...),
        'ttl': (Optional[int], None)
    }

    async def before_resolve(self, query, response, *args, **kwargs):
        redis_key = self.config.redis_key_A
        default_ip = [x.__str__() for x in self.config.response_ip]
        ttl = self.config.ttl or self.config.default_ttl
        rrset = DNS.Utilities.create_rrset(dns.rdatatype.A, '_', addresses=default_ip, ttl=ttl)
        for q_ in query.question:
            if q_.rdtype == dns.rdatatype.A:
                name = q_.name
                result = await self.redis_iterative_lookup(redis_key, name, 'sismember')
                if not result:
                    continue
                logger.info(f'{name.to_text()} is black listed. modifying ...')
                rrset_ = copy.deepcopy(rrset)
                rrset_.name = q_.name
                self._manual_answer(query.question, q_, response.answer, rrset_)
        return query, response

    async def after_resolve(self, query, response, *args, **kwargs):
        return query, response


class WhiteList(_Authoritative):
    """
    response all questions with predefined ip except some hosts defined in redis db which will be untouched
    notes:
        - currently just supports "A" type question and response
        - domains should be stored in db without trailing dot
        - subdomain wildcard is supported (e.g. *.google.com)
    """

    CONFIG = {
        'redis_key_A': (str, 'WLDB'),
        'response_ip': (List[IPv4Address], ...),
        'ttl': (Optional[int], None)
    }

    async def before_resolve(self, query, response, *args, **kwargs):
        redis_key = self.config.redis_key_A
        default_ip = [x.__str__() for x in self.config.response_ip]
        ttl = self.config.ttl or self.config.default_ttl
        rrset = DNS.Utilities.create_rrset(dns.rdatatype.A, '_', addresses=default_ip, ttl=ttl)
        for q_ in query.question:
            if q_.rdtype == dns.rdatatype.A:
                name = q_.name
                result = await self.redis_iterative_lookup(redis_key, name, 'sismember')
                if result:
                    logger.info(f'{name.to_text()} is white listed. skipping ...')
                    continue
                rrset_ = copy.deepcopy(rrset)
                rrset_.name = q_.name
                self._manual_answer(query.question, q_, response.answer, rrset_)
        return query, response

    async def after_resolve(self, query, response, *args, **kwargs):
        return query, response
