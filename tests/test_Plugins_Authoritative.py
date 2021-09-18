# noinspection PyPackageRequirements

import fakeredis.aioredis
import pytest

from tests.helpers import extract_address_from_a_response as eafar
from tests.test_Basic import _TestBase


class _AuthoritativeTestBase(_TestBase):
    FAKE_REC = {
        'domain': 'test.com',
        'subdomain_1': 'test.test.com',
        'subdomain_2': 'test2.test.com',
        'wildcard': '*.test.com',
        'ip': {"1.2.3.4", "5.6.7.8"},
    }

    def redis_key(self, server_conf):
        return getattr(server_conf, self._redis_key)

    @staticmethod
    def ip2rec(ip):
        return ';'.join(ip)

    @pytest.fixture(scope='class')
    def assert_real(self, local_remote_equality_assert):
        async def _is_real(host):
            await local_remote_equality_assert(host)

        return _is_real

    @pytest.fixture(scope='class')
    def assert_fake(self, resolve_local_a):
        async def _is_fake(host):
            local = await resolve_local_a(host)
            fake = self.FAKE_REC['ip']
            assert eafar(local) == fake

        return _is_fake

    @pytest.fixture(scope='class')
    def redis(self, server):
        redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        server.plugins[0].redis = redis
        yield redis

    @pytest.fixture(scope='function')
    async def redis_hset(self, redis):
        created_records = []

        async def _hset(name, key, value):
            await redis.hset(name, key, value)
            created_records.append(dict(name=name, key=key))

        yield _hset
        for record in created_records:
            await redis.hdel(record['name'], record['key'])

    @pytest.fixture(scope='function')
    async def redis_sadd(self, redis):
        created_records = []

        async def _sadd(key, value):
            await redis.sadd(key, value)
            created_records.append(dict(key=key, val=value))

        yield _sadd
        for record in created_records:
            await redis.srem(record['key'], record['val'])


class _TestLocalDB(_AuthoritativeTestBase):
    _redis_key = 'Plugin__Authoritative.LocalDB__redis_key_A'

    async def test_other(self, assert_real, redis_hset, server_conf):
        key = self.redis_key(server_conf)
        await assert_real(self.EXAMPLE_HOST)
        await redis_hset(key, self.FAKE_REC['domain'], self.ip2rec(self.FAKE_REC['ip']))
        await assert_real(self.EXAMPLE_HOST)

    async def test_domain(self, assert_real, assert_fake, redis_hset, server_conf):
        key = self.redis_key(server_conf)
        await redis_hset(key, self.FAKE_REC['domain'], self.ip2rec(self.FAKE_REC['ip']))
        await assert_fake(self.FAKE_REC['domain'])
        await assert_real(self.FAKE_REC['subdomain_1'])
        await assert_real(self.FAKE_REC['subdomain_2'])

    async def test_subdomain(self, assert_real, assert_fake, redis_hset, server_conf):
        key = self.redis_key(server_conf)
        await redis_hset(key, self.FAKE_REC['subdomain_1'], self.ip2rec(self.FAKE_REC['ip']))
        await assert_real(self.FAKE_REC['domain'])
        await assert_fake(self.FAKE_REC['subdomain_1'])
        await assert_real(self.FAKE_REC['subdomain_2'])

    async def test_subdomain_wildcard(self, assert_real, assert_fake, redis_hset, server_conf):
        key = self.redis_key(server_conf)
        await redis_hset(key, self.FAKE_REC['wildcard'], self.ip2rec(self.FAKE_REC['ip']))
        await assert_real(self.FAKE_REC['domain'])
        await assert_fake(self.FAKE_REC['subdomain_1'])
        await assert_fake(self.FAKE_REC['subdomain_2'])

    async def test_domain_wildcard(self, assert_real, assert_fake, redis_hset, server_conf):
        key = self.redis_key(server_conf)
        await redis_hset(key, self.FAKE_REC['domain'], self.ip2rec(self.FAKE_REC['ip']))
        await redis_hset(key, self.FAKE_REC['wildcard'], self.ip2rec(self.FAKE_REC['ip']))
        await assert_fake(self.FAKE_REC['domain'])
        await assert_fake(self.FAKE_REC['subdomain_1'])
        await assert_fake(self.FAKE_REC['subdomain_2'])


class _TestBlackList(_AuthoritativeTestBase):
    _redis_key = 'Plugin__Authoritative.BlackList__redis_key_A'

    async def test_other(self, assert_real, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await assert_real(self.EXAMPLE_HOST)
        await redis_sadd(key, self.FAKE_REC['domain'])
        await assert_real(self.EXAMPLE_HOST)

    async def test_domain(self, assert_real, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await redis_sadd(key, self.FAKE_REC['domain'])
        await assert_fake(self.FAKE_REC['domain'])
        await assert_real(self.FAKE_REC['subdomain_1'])
        await assert_real(self.FAKE_REC['subdomain_2'])

    async def test_subdomain(self, assert_real, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await redis_sadd(key, self.FAKE_REC['subdomain_1'])
        await assert_real(self.FAKE_REC['domain'])
        await assert_fake(self.FAKE_REC['subdomain_1'])
        await assert_real(self.FAKE_REC['subdomain_2'])

    async def test_subdomain_wildcard(self, assert_real, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await redis_sadd(key, self.FAKE_REC['wildcard'])
        await assert_real(self.FAKE_REC['domain'])
        await assert_fake(self.FAKE_REC['subdomain_1'])
        await assert_fake(self.FAKE_REC['subdomain_2'])

    async def test_domain_wildcard(self, assert_real, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await redis_sadd(key, self.FAKE_REC['domain'])
        await redis_sadd(key, self.FAKE_REC['wildcard'])
        await assert_fake(self.FAKE_REC['domain'])
        await assert_fake(self.FAKE_REC['subdomain_1'])
        await assert_fake(self.FAKE_REC['subdomain_2'])


class _TestWhiteList(_AuthoritativeTestBase):
    _redis_key = 'Plugin__Authoritative.WhiteList__redis_key_A'

    async def test_other(self, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await assert_fake(self.EXAMPLE_HOST)
        await redis_sadd(key, self.FAKE_REC['domain'])
        await assert_fake(self.EXAMPLE_HOST)

    async def test_domain(self, assert_real, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await redis_sadd(key, self.FAKE_REC['domain'])
        await assert_real(self.FAKE_REC['domain'])
        await assert_fake(self.FAKE_REC['subdomain_1'])
        await assert_fake(self.FAKE_REC['subdomain_2'])

    async def test_subdomain(self, assert_real, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await redis_sadd(key, self.FAKE_REC['subdomain_1'])
        await assert_fake(self.FAKE_REC['domain'])
        await assert_real(self.FAKE_REC['subdomain_1'])
        await assert_fake(self.FAKE_REC['subdomain_2'])

    async def test_subdomain_wildcard(self, assert_real, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await redis_sadd(key, self.FAKE_REC['wildcard'])
        await assert_fake(self.FAKE_REC['domain'])
        await assert_real(self.FAKE_REC['subdomain_1'])
        await assert_real(self.FAKE_REC['subdomain_2'])

    async def test_domain_wildcard(self, assert_real, assert_fake, redis_sadd, server_conf):
        key = self.redis_key(server_conf)
        await redis_sadd(key, self.FAKE_REC['domain'])
        await redis_sadd(key, self.FAKE_REC['wildcard'])
        await assert_real(self.FAKE_REC['domain'])
        await assert_real(self.FAKE_REC['subdomain_1'])
        await assert_real(self.FAKE_REC['subdomain_2'])


server_config = {
    'DNSPY__PLUGIN__AUTHORITATIVE__REDIS_URI': 'redis://mock:1234/0'
}

server_config_localdb = {
    **server_config,
    'DNSPY__PLUGINS': ["Authoritative.LocalDB"],
}
server_config_blacklist = {
    **server_config,
    'DNSPY__PLUGINS': '["Authoritative.BlackList"]',
    'DNSPY__PLUGIN__AUTHORITATIVE.BLACKLIST__RESPONSE_IP': list(_AuthoritativeTestBase.FAKE_REC['ip'])
}
server_config_whitelist = {
    **server_config,
    'DNSPY__PLUGINS': '["Authoritative.WhiteList"]',
    'DNSPY__PLUGIN__AUTHORITATIVE.WHITELIST__RESPONSE_IP': list(_AuthoritativeTestBase.FAKE_REC['ip'])
}


@pytest.mark.parametrize('server_conf', [server_config_localdb], indirect=['server_conf'])
class TestLocalDB(_TestLocalDB):
    pass


@pytest.mark.parametrize('server_conf', [server_config_blacklist], indirect=['server_conf'])
class TestBlackList(_TestBlackList):
    pass


@pytest.mark.parametrize('server_conf', [server_config_whitelist], indirect=['server_conf'])
class TestWhiteList(_TestWhiteList):
    pass
