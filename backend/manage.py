#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # `manage.py test` gets its own settings: no Redis, no broker, no SMTP and
    # no rate limiting. This has to overwrite DJANGO_SETTINGS_MODULE rather
    # than setdefault it -- CI exports the development module for the other
    # management commands in the job, and setdefault would silently lose to it
    # and run the suite against production throttle rates. Pass --settings
    # explicitly to override this.
    argv = sys.argv[1:]
    if argv and argv[0] == 'test' and not any(
        arg == '--settings' or arg.startswith('--settings=') for arg in argv
    ):
        os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.test'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
