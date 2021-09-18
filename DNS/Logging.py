import os
import sys

import loguru

logger = loguru.logger


def reload():
    kwargs = _loguru_envargs()
    logger.remove()
    logger.add(sys.stdout, **kwargs)


# noinspection PyUnresolvedReferences,PyProtectedMember
def _loguru_envargs():
    env = loguru._defaults.env
    types = {x: type(y) for x, y in loguru._defaults.__dict__.items() if x.startswith('LOGURU_')}
    argset = dict(
        level="LOGURU_LEVEL",
        format="LOGURU_FORMAT",
        filter="LOGURU_FILTER",
        colorize="LOGURU_COLORIZE",
        serialize="LOGURU_SERIALIZE",
        backtrace="LOGURU_BACKTRACE",
        diagnose="LOGURU_DIAGNOSE",
        enqueue="LOGURU_ENQUEUE",
        catch="LOGURU_CATCH"
    )
    kwargs = {}
    for i_, j_ in argset.items():
        if j_ in os.environ.keys():
            kwargs[i_] = env(j_, types[j_], None)
    return kwargs


reload()
