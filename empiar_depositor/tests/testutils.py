import os
import unittest
import sys
from contextlib import contextmanager

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


class EmpiarDepositorTest(unittest.TestCase):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "deposition_json/working_example.json")
    thumbnail_path = os.path.join(current_dir, "img/entry_thumbnail.gif")


@contextmanager
def capture(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, StringIO()
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out
