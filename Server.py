import argparse
import asyncio
import atexit
import copy
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
    parser.add_argument('--list-env', action='store_true', help='show all available env. variables options')
    parser.add_argument('--list-plugin', action='store_true', help='show all available plugins')
    args = parser.parse_args()
    if args.env_file:
        dotenv.load_dotenv(args.env_file)

    return args


class HelpPrinter:
    sep_1 = '=' * 70
    sep_2 = '-' * 30
    sep_3 = '-' * 20
    sep_4 = ':' * 15

    @classmethod
    def print_list_env(cls):
        def _print_env_data(data: dict):
            data: dict = copy.deepcopy(data)
            print(', '.join(data.pop('env_names')).upper())
            for i__ in ['title', 'default', 'type']:
                v_ = data.pop(i__, None)
                if v_:
                    print('\t', i__, ':', v_)
            for i__, v_ in data.items():
                print('\t', i__, ':', v_)
            print()

        print(cls.sep_1)
        print('server config options:')
        print(cls.sep_2)
        DNS.Config.Configuration.load(active_all_plugins=True)
        conf = DNS.Config.Settings.schema()['properties']
        plugin_conf = {}
        for i_, j_ in conf.items():
            if i_.startswith('Plugin__'):
                key_p = i_.split('__')[1]
                key_m = key_p.split('.')[0]
                key_c = key_p.split('.')[1] if '.' in key_p else '__module__'
                if key_m not in plugin_conf.keys():
                    plugin_conf[key_m] = {}
                if key_c not in plugin_conf[key_m].keys():
                    plugin_conf[key_m][key_c] = []
                plugin_conf[key_m][key_c].append(i_)
                continue
            _print_env_data(j_)
        print(cls.sep_1)
        print('plugins config options:')
        for i_, j_ in plugin_conf.items():
            print(cls.sep_3)
            print(f'plugin {i_}')
            c_ = 0
            for k_, l_ in j_.items():
                if len(l_) == 0:
                    continue
                c_ += 1
                print(cls.sep_4)
                print(f'{c_}.', end=' ')
                if k_ == '__module__':
                    print(i_, end=' ')
                else:
                    print('.'.join([i_, k_]), end=' ')
                print(':')
                print()
                for m_ in l_:
                    _print_env_data(conf[m_])

    @classmethod
    def print_list_plugin(cls):
        print(cls.sep_1)
        print('available plugins:')
        for i_, j_ in DNS.Config.Configuration.get_all_plugins().items():
            print(cls.sep_2)
            print(i_)
            print(cls.sep_4)
            print(j_.__doc__)
            print()


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
    if args_.list_env or args_.list_plugin:
        if args_.list_env:
            HelpPrinter.print_list_env()
        if args_.list_plugin:
            HelpPrinter.print_list_plugin()
    else:
        main()
