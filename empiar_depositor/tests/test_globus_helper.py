import unittest
import json
import os
from unittest.mock import patch, MagicMock

from empiar_depositor.empiar_depositor import GlobusHelper


class TestGlobusHelper(unittest.TestCase):

    def setUp(self):
        self.endpoint_param = "test-endpoint-uuid"
        self.local_path = "/path/to/data"
        self.helper = GlobusHelper(self.endpoint_param, self.local_path)

    @patch('empiar_depositor.empiar_depositor.run_shell_command')
    def test_login_and_identify_success(self, mock_run):
        # Implementation checks for bytes in the output
        mock_run.side_effect = [
            (b"You are already logged in", b"", 0),
            (b"testuser@globusid.org", b"", 0)
        ]

        result = self.helper.login_and_identify()

        self.assertTrue(result)
        self.assertEqual(self.helper.user_identity, "testuser@globusid.org")
        self.assertEqual(mock_run.call_count, 2)

    @patch('empiar_depositor.empiar_depositor.run_shell_command')
    def test_check_local_endpoint_id_found(self, mock_run):
        self.helper.user_identity = "testuser@globusid.org"

        # Code calls json.loads(out), which works on bytes or strings
        mock_json = json.dumps({
            "DATA": [
                {"display_name": "wrong-one", "id": "123"},
                {"display_name": "test-endpoint-uuid", "id": "target-uuid-456"}
            ]
        }).encode('utf-8')

        mock_run.return_value = (mock_json, b"", 0)

        result = self.helper.check_local_endpoint_id()

        self.assertTrue(result)
        self.assertEqual(self.helper.endpoint_id, "target-uuid-456")

    @patch('empiar_depositor.empiar_depositor.os.path.isdir', return_value=True)
    @patch('empiar_depositor.empiar_depositor.run_shell_command')
    def test_validate_path_access_directory(self, mock_run, mock_isdir):
        self.helper.endpoint_id = "target-uuid-456"
        # Return valid JSON for the 'globus ls' check
        mock_run.return_value = (b'{"DATA": []}', b"", 0)

        result = self.helper.validate_path_access("/path/to/data")

        self.assertTrue(result)
        self.assertEqual(self.helper.dir_flag, "-r")
        self.assertEqual(self.helper.obj_name, "data")

    @patch('empiar_depositor.empiar_depositor.run_shell_command')
    def test_globus_upload_initiation(self, mock_run):
        self.helper.endpoint_id = "source-uuid"
        self.helper.obj_name = "data"
        self.helper.dir_flag = "-r"
        self.helper.local_data_path = "/path/to/data"

        mock_init_json = json.dumps({"task_id": "transfer-task-123"}).encode('utf-8')

        # First call: globus transfer, Second call: globus task wait
        mock_run.side_effect = [
            (mock_init_json, b"", 0),
            (b"Task completed", b"", 0)
        ]

        result = self.helper.globus_upload("dest-dir", "dest-endpoint-uuid")

        self.assertEqual(result['status'], 'COMPLETED')

        # Verify call arguments for transfer command
        args, _ = mock_run.call_args_list[0]
        cmd_list = args[0]
        self.assertIn("globus", cmd_list)
        self.assertIn("transfer", cmd_list)
        self.assertIn("-r", cmd_list)

    @patch('empiar_depositor.empiar_depositor.run_shell_command')
    def test_login_failure(self, mock_run):
        # Code explicitly looks for 'Error' or non-zero code
        mock_run.return_value = (b"General Failure", b"Invalid credentials", 1)

        with self.assertRaises(Exception) as context:
            self.helper.login_and_identify()

        self.assertIn("Globus login failed", str(context.exception))
        self.assertEqual(self.helper.helper_status, "ERRORED 2 A")


if __name__ == '__main__':
    unittest.main()