import os
import unittest
import sys
from contextlib import contextmanager
from mock import Mock, PropertyMock
from requests.models import Response
from requests.structures import CaseInsensitiveDict

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

def mock_response(mocked_response=None, status_code=None, headers=None, json=None):
    mocked_response.return_value = Mock(ok=True, spec=Response)

    if status_code:
        mocked_response.return_value.status_code = status_code

    if headers:
        type(mocked_response.return_value).headers = PropertyMock(return_value=CaseInsensitiveDict())
        mocked_response.return_value.headers.get = Mock()
        mocked_response.return_value.headers.get.side_effect = lambda header: headers[header]

    if json:
        mocked_response.return_value.json.return_value = json

    return mocked_response
