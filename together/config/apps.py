
import os

from django.apps import AppConfig
from django.conf import settings


class ConfigAppConfig(AppConfig):
    name = 'config'

    def ready(self):

        if os.environ.get('RUN_MAIN', None) == 'true':
            return

        if not settings.DEBUG:
            return

        from functools import reduce

        class Colors:
            HEADER = '\033[95m'
            BLUE = '\033[94m'
            GREEN = '\033[92m'
            YELLOW = '\033[93m'
            RED = '\033[91m'
            END = '\033[0m'
            BOLD = '\033[1m'
            UNDERLINE = '\033[4m'

        def color_string(string, colors):
            return reduce(lambda a, b: a + b, colors) + string + Colors.END

        def colored_print(string, colors):
            print(color_string(string, colors))

        db = settings.DATABASES['default']
        info = getattr(settings, 'ENVIRONMENT_TYPE')

        modes = {key: value for key, value in [
            ('DEBUG', getattr(settings, 'DEBUG', None)),
            # add more boolean modes here to be printed on runserver
        ]}

        if info:
            colored_print(f"ENVIRONMENT: <{info}>", Colors.BLUE)

        if db:
            host = db.get('HOST', None)
            port = db.get('PORT', None)
            engine = db.get('ENGINE', None)
            name = db.get('NAME', None)

            host_port = f" at {host}:{port}" if host and port else ''
            engine = engine.split('.')[-1] if engine else ''

            colored_print(f"Connected to {engine} database\n{name}{host_port}",
                          [Colors.BOLD, Colors.YELLOW])

        if modes:
            print(
                f"Modes: {', '.join([color_string(key, (Colors.RED, Colors.GREEN)[value]) for key, value in modes.items()])}")
