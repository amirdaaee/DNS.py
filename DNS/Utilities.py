import asyncio
import copy

import dns.rdtypes
import dns.rdtypes.IN.A

from DNS.Logging import logger


def create_rrset(rdatatype, name, **kwargs):
    switch = {
        dns.rdatatype.A: _create_rrset_a
    }
    if rdatatype not in switch.keys():
        raise NotImplementedError('selected rdatatype is not implanted yet')
    else:
        rrset = switch[rdatatype](name, **kwargs)
    return rrset


def create_rdata(rdatatype, **kwargs):
    switch = {
        dns.rdatatype.A: _create_rdata_a
    }
    if rdatatype not in switch.keys():
        raise NotImplementedError('selected rdatatype is not implanted yet')
    else:
        rdata = switch[rdatatype](**kwargs)
    return rdata


def _create_rdata_a(address):
    rdata = dict(rdclass=dns.rdataclass.IN, rdtype=dns.rdatatype.A)
    return dns.rdtypes.IN.A.A(address=address, **rdata)


def _create_rrset_a(name: str, addresses: list, ttl):
    resp = []
    for r_ in addresses:
        resp.append(create_rdata(dns.rdatatype.A, address=r_))
    resp = dns.rrset.from_rdata_list(name, ttl, resp)
    return resp


async def async_iterative_lookup(name, func, tailing_dot=False):
    _name = copy.deepcopy(name)
    search = _name.to_text((not tailing_dot))
    while True:
        result = await func(search)
        if _name == dns.name.root or result:
            logger.debug(f'result for {name.to_text()} at {search} : {result}')
            break
        _name = _name.parent()
        search = '*.' + _name.to_text((not tailing_dot))
    return result


def iterative_lookup(name, func, tailing_dot=False):
    return asyncio.run(async_iterative_lookup(name, func, tailing_dot))
