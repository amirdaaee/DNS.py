import json
import os

import dns.asyncresolver
import pytest

import DNS.Config
import DNS.Core
from tests.helpers import extract_address_from_a_response as eafar


@pytest.mark.asyncio
class _TestBase:
    CONFIG_BASE = {
        "DNSPY__LOCAL_IP": "127.0.0.1",
        "DNSPY__LOCAL_PORT": 5053,
        "DNSPY__UPSTREAM_IP": '8.8.8.8',
        "DNSPY__UPSTREAM_PORT": 53,
        "DNSPY__PLUGINS_POST": ['QueryLog.log'],
        "LOGURU_LEVEL": 'DEBUG'
    }
    EXAMPLE_HOST = 'example.com'

    @staticmethod
    def _resolve_factory(where, conf):
        resolver = dns.asyncresolver.Resolver()
        if where == 'local':
            ns = conf.local_ip.__str__()
            port = conf.local_port
        else:
            ns = conf.upstream_ip.__str__()
            port = conf.upstream_port
        resolver.nameservers = [ns]
        resolver.port = port

        async def _resolver(host):
            return await resolver.resolve(host)

        return _resolver

    @staticmethod
    def equality_assert(resp_a, resp_b):
        a = eafar(resp_a)
        b = eafar(resp_b)
        assert a == b

    @pytest.fixture(scope='class')
    def server_conf(self, request, monkeyclass):
        monkeyclass.chdir('../')
        if hasattr(request, 'param'):
            conf = request.param
        else:
            conf = {}
        cfg = {}
        cfg.update(self.CONFIG_BASE)
        cfg.update(conf)
        for i, j in cfg.items():
            if type(j) is str:
                j_ = j
            else:
                j_ = json.dumps(j)
            monkeyclass.setenv(i, j_)
        DNS.Config.Configuration.load()
        config = DNS.Config.Settings
        print(config)
        yield config
        os.remove(DNS.Config.Configuration.RUNTIME_FILE)

    @pytest.fixture(scope='class')
    async def server(self, server_conf):
        server = DNS.Core.UDPDNSServer()
        await server.start()
        yield server
        await server.stop()

    @pytest.fixture(scope='class')
    def resolve_remote_a(self, server_conf):
        return self._resolve_factory('remote', server_conf)

    @pytest.fixture(scope='class')
    def resolve_local_a(self, server_conf, server):
        return self._resolve_factory('local', server_conf)

    @pytest.fixture(scope='class')
    def local_remote_equality_assert(self, resolve_remote_a, resolve_local_a):
        async def _assert(host):
            self.equality_assert(await resolve_local_a(host), await resolve_remote_a(host))

        return _assert


@pytest.mark.parametrize('server_conf', [{}, {'DNSPY__LOCAL_PORT': '5054'}], indirect=['server_conf'])
class TestBasic(_TestBase):
    async def test_basic(self, local_remote_equality_assert):
        await local_remote_equality_assert(self.EXAMPLE_HOST)
