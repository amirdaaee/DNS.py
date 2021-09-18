import argparse
import asyncio
import atexit
import os

import aiorun
import dotenv

import DNS.Config
import DNS.Core
from DNS.Logging import logger


def read_cli():
    parser = argparse.ArgumentParser(description='Start a DNS proxy server')
    parser.add_argument('--env-file', default=None, type=str, help='path to env file for configuration',
                        metavar='path')
    args = parser.parse_args()
    if args.env_file:
        dotenv.load_dotenv(args.env_file)

    return args


def main():
    def _clean_exit():
        logger.info('server shutdown')

    atexit.register(_clean_exit)
    DNS.Config.Configuration.load()
    print(f'configuration: {DNS.Config.Settings.json()}')
    loop = asyncio.get_event_loop()
    loop.create_task(DNS.Core.UDPDNSServer().start())
    aiorun.run(loop=loop, executor_workers=2)


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    args_ = read_cli()
    main()
