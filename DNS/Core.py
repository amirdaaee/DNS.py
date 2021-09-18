import asyncio
import importlib
from abc import abstractmethod

import dns.asyncquery
import dns.message

import DNS.Config
from DNS.Logging import logger


class UDPAsyncServer(asyncio.protocols.DatagramProtocol):
    transport: asyncio.transports.BaseTransport = None

    def __init__(self, *args, **kwargs):
        self.local_addr = (DNS.Config.Settings.local_ip.__str__(), DNS.Config.Settings.local_port)

    def factory(self):
        return self

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        logger.debug(f'received an udp data from {addr}:{data}')
        loop = asyncio.get_event_loop()
        loop.create_task(self.handle_inbound_packet(data, addr))

    @abstractmethod
    async def handle_inbound_packet(self, data, addr):
        raise NotImplementedError('handle_inbound_packet is not defined')

    async def start(self):
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(self.factory, local_addr=self.local_addr)
        logger.info('server started')

    async def stop(self):
        self.transport.close()
        logger.info('server stopped')


class UDPDNSServer(UDPAsyncServer):
    def __init__(self, *args, **kwargs):
        super(UDPDNSServer, self).__init__(*args, **kwargs)

        plugins = []
        for i_ in DNS.Config.Settings.plugins:
            module_, class_ = i_.split('.')
            module = f'{DNS.Config.Configuration.PLUGIN_PACKAGE}.{module_}'
            module = importlib.import_module(module)
            plugins.append(getattr(module, class_)(plugins))
        self.plugins = plugins
        pass

    @staticmethod
    async def _run_func_or_coroutine(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    async def handle_inbound_packet(self, data, addr):
        query = dns.message.from_wire(data, 0)
        resp = dns.message.make_response(query, recursion_available=True)
        query_str = query.to_text().replace('\n', '\\n')
        logger.debug(f'reading DNS query from {addr}: {query_str}')
        for f_ in self.plugins:
            query, resp = await self._run_func_or_coroutine(f_.before_resolve, query, resp, addr)
        if len(query.question) > 0:
            resp_ = await dns.asyncquery.udp(
                query,
                DNS.Config.Settings.upstream_ip.__str__(),
                port=DNS.Config.Settings.upstream_port
            )
            resp.answer += resp_.answer
        for f_ in self.plugins:
            query, resp = await self._run_func_or_coroutine(f_.after_resolve, query, resp, addr)
        resp_str = resp.to_text().replace('\n', '\\n')
        logger.debug(f'writing DNS query to {addr}: {resp_str}')
        self.transport.sendto(resp.to_wire(), addr)
