import asyncio

import pytest
from pytest import MonkeyPatch


@pytest.fixture(scope='class')
def monkeyclass():
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope='class')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()
