import sys
from contextlib import contextmanager

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


@contextmanager
def capture(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, StringIO()
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out
