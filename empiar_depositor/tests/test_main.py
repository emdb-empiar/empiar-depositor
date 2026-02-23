import unittest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
from requests.models import Response

from empiar_depositor.empiar_depositor import (
    EmpiarDepositor,
    GlobusHelper,
    run_shell_command,
    check_json_response,
    validate_empiar_json
)


class TestEmpiarDepositor(unittest.TestCase):

    def setUp(self):
        self.params = {
            "empiar_token": "mock-token",
            "json_input": "metadata.json",
            "server_root": "https://www.ebi.ac.uk",
            "data": "/mock/data",
            "globus_source_endpoint": "endpoint-uuid",
            "ignore_certificate": True,
            "entry_thumbnail": "thumb.png",
            "globus_local_username": "test_user"
        }
        self.depositor = EmpiarDepositor(**self.params)

    @patch('empiar_depositor.empiar_depositor.time.sleep', return_value=None)
    @patch('empiar_depositor.empiar_depositor.EmpiarDepositor.make_request')
    def test_create_new_deposition_with_polling(self, mock_make_request, mock_sleep):
        res_post = MagicMock(spec=Response)
        res_post.status_code = 201
        res_post.headers = {'content-type': 'application/json'}
        res_post.json.return_value = {
            'deposition': True,
            'entry_id': '123',
            'directory': 'In progress'
        }

        res_poll = MagicMock(spec=Response)
        res_poll.status_code = 200
        res_poll.headers = {'content-type': 'application/json'}
        res_poll.json.return_value = {
            'status': 'Completed',
            'return_value': 'final_dir'
        }

        mock_make_request.side_effect = [res_post, res_poll]

        with patch('builtins.open', mock_open(read_data='{}')):
            result = self.depositor.create_new_deposition()

        self.assertTrue(result)
        self.assertEqual(self.depositor.entry_directory, 'final_dir')

    @patch('empiar_depositor.empiar_depositor.check_json_response', return_value=True)
    @patch('empiar_depositor.empiar_depositor.EmpiarDepositor.make_request')
    def test_share_upload_directory_success(self, mock_make_request, mock_check):
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = json.dumps({"response": ["1", "Success"]})
        mock_make_request.return_value = mock_response

        result = self.depositor.share_upload_directory()
        self.assertTrue(result)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_thumbnail_upload_failure(self, mock_post):
        mock_response = MagicMock(spec=Response)
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'thumbnail_upload': False}
        mock_post.return_value = mock_response

        with patch('builtins.open', mock_open(read_data=b'fake-binary')):
            result = self.depositor.thumbnail_upload()
        self.assertFalse(result)


class TestGlobusHelper(unittest.TestCase):

    def setUp(self):
        self.helper = GlobusHelper("test-endpoint", "/local/path")

    @patch('empiar_depositor.empiar_depositor.run_shell_command')
    def test_login_and_identify_success(self, mock_run):
        mock_run.side_effect = [
            (b"You are already logged in", b"", 0),
            (b"user@globusid.org", b"", 0)
        ]
        self.assertTrue(self.helper.login_and_identify())
        self.assertEqual(self.helper.user_identity, "user@globusid.org")

    @patch('empiar_depositor.empiar_depositor.run_shell_command')
    def test_check_local_endpoint_id(self, mock_run):
        self.helper.user_identity = "user@globusid.org"
        mock_data = json.dumps({"DATA": [{"display_name": "test-endpoint", "id": "uuid-123"}]})
        mock_run.return_value = (mock_data.encode(), b"", 0)

        self.assertTrue(self.helper.check_local_endpoint_id())
        self.assertEqual(self.helper.endpoint_id, "uuid-123")

    @patch('empiar_depositor.empiar_depositor.os.path.isdir', return_value=True)
    @patch('empiar_depositor.empiar_depositor.run_shell_command')
    def test_validate_path_access(self, mock_run, mock_isdir):
        self.helper.endpoint_id = "uuid-123"
        mock_run.return_value = (b'{"DATA": []}', b"", 0)
        self.assertTrue(self.helper.validate_path_access("/path/data"))
        self.assertEqual(self.helper.obj_name, "data")


class TestUtilities(unittest.TestCase):

    def test_run_shell_command(self):
        out, err, code = run_shell_command(['echo', 'test'])
        self.assertEqual(out.strip(), b'test')
        self.assertEqual(code, 0)

    def test_check_json_response(self):
        res = MagicMock(spec=Response)
        res.headers = {'content-type': 'application/json'}
        self.assertTrue(check_json_response(res))

    @patch('empiar_depositor.empiar_depositor.os.path.exists', return_value=False)
    def test_validate_empiar_json_no_schema(self, mock_exists):
        with patch('builtins.print'):
            self.assertTrue(validate_empiar_json('in.json', 'no_schema.json'))

    @patch('empiar_depositor.empiar_depositor.os.path.exists', return_value=True)
    @patch('empiar_depositor.empiar_depositor.validate')
    def test_validate_empiar_json_success(self, mock_validate, mock_exists):
        m_open = mock_open()
        m_open.side_effect = [
            mock_open(read_data='{"type": "object"}').return_value,
            mock_open(read_data='{"entry": "data"}').return_value
        ]
        with patch('builtins.open', m_open), patch('builtins.print'):
            self.assertTrue(validate_empiar_json('in.json', 'schema.json'))


@patch('empiar_depositor.empiar_depositor.argparse.ArgumentParser.parse_args')
@patch('empiar_depositor.empiar_depositor.validate_empiar_json', return_value=True)
@patch('empiar_depositor.empiar_depositor.GlobusHelper')
@patch('empiar_depositor.empiar_depositor.EmpiarDepositor')
@patch('empiar_depositor.empiar_depositor.os.path.isfile', return_value=True)
def test_main_workflow(mock_isfile, mock_dep_class, mock_globus_class, mock_val, mock_args):
    from empiar_depositor.empiar_depositor import main

    mock_args.return_value = MagicMock(
        empiar_token="token", json_input="j.json", data="d/", globus="g",
        globus_force_login=False, entry_thumbnail=None, password=None,
        resume=None, stop_submit=False, ignore_certificate=True,
        development=True, output_id_dir=False, grant_rights_usernames=None,
        grant_rights_emails=None, grant_rights_orcids=None
    )

    mock_globus = mock_globus_class.return_value
    mock_globus.validate_globus_details.return_value = {'status': 'COMPLETED', 'error_message': None}
    mock_globus.user_identity = "user@globus"
    mock_globus.globus_upload.return_value = {'status': 'COMPLETED', 'error_message': None}

    mock_dep = mock_dep_class.return_value
    mock_dep.create_new_deposition.return_value = True
    mock_dep.share_upload_directory.return_value = True
    mock_dep.acknowledge_completion.return_value = True
    mock_dep.submit_deposition.return_value = True
    mock_dep.entry_id, mock_dep.entry_directory, mock_dep.empiar_accession = "1", "dir", "ACC"

    with patch('sys.stdout', new=MagicMock()):
        try:
            main()
        except SystemExit:
            pass

    mock_dep.create_new_deposition.assert_called_once()
    mock_globus.globus_upload.assert_called_once()


if __name__ == '__main__':
    unittest.main()
