import json
import unittest
from unittest.mock import patch, MagicMock

from empiar_depositor.empiar_depositor import GlobusHelper, CliError


class TestGlobusHelper(unittest.TestCase):
    """
    Unit tests for the GlobusHelper class to ensure correct interaction
    with the Globus CLI and appropriate error handling during data transfer.
    """

    def setUp(self):
        """
        Initializes common test parameters and a mock logger for each test case.
        """
        self.endpoint_param = "test-endpoint-uuid"
        self.local_path = "/path/to/data"
        self.log = MagicMock()
        self.helper = GlobusHelper(logger=self.log)

    @patch("empiar_depositor.empiar_depositor.run_shell_command")
    def test_login_and_identify_success(self, mock_run):
        """
        Tests successful authentication and identity retrieval using Globus CLI.
        """
        # Mock sequence: 1. globus login check, 2. globus whoami
        mock_run.side_effect = [
            (b"You are already logged in", b"", 0),
            (b"testuser@globusid.org\n", b"", 0),
        ]

        self.helper.login_and_identify()

        self.assertEqual(self.helper.user_identity, "testuser@globusid.org")
        self.assertEqual(mock_run.call_count, 2)

    @patch("empiar_depositor.empiar_depositor.run_shell_command")
    def test_check_local_endpoint_id_found(self, mock_run):
        """
        Verifies that the helper correctly identifies a specific endpoint UUID
        from a list of available Globus endpoints.
        """
        self.helper.user_identity = "testuser@globusid.org"

        mock_json = json.dumps({
            "DATA": [
                {"display_name": "wrong-one", "id": "123"},
                {"display_name": "test-endpoint-uuid", "id": "target-uuid-456"},
            ]
        }).encode("utf-8")

        mock_run.return_value = (mock_json, b"", 0)

        self.helper.check_local_endpoint_id(self.endpoint_param)

        self.assertEqual(self.helper.endpoint_id, "target-uuid-456")

    @patch("empiar_depositor.empiar_depositor.os.path.isfile", return_value=False)
    @patch("empiar_depositor.empiar_depositor.os.path.isdir", return_value=True)
    @patch("empiar_depositor.empiar_depositor.run_shell_command")
    def test_validate_path_access_directory(self, mock_run, mock_isdir, mock_isfile):
        """
        Tests that the helper correctly identifies a directory for upload and
        constructs the appropriate 'globus ls' command.
        """
        self.helper.endpoint_id = "target-uuid-456"
        mock_run.return_value = (b'{"DATA": []}', b"", 0)

        self.helper.validate_path_access(self.local_path)

        self.assertEqual(self.helper.dir_flag, "-r")
        self.assertEqual(self.helper.obj_name, "data")
        self.assertEqual(self.helper.endpoint_path, self.local_path)

        # Ensure the system call included correct endpoint formatting and JSON flags
        args, _ = mock_run.call_args
        cmd = args[0]
        self.assertIn("globus", cmd)
        self.assertIn("ls", cmd)
        self.assertIn("--format", cmd)
        self.assertIn("json", cmd)
        self.assertTrue(any(part.startswith("target-uuid-456:") for part in cmd))

    @patch("empiar_depositor.empiar_depositor.run_shell_command")
    def test_globus_upload_initiation(self, mock_run):
        """
        Verifies the full transfer sequence: initiating the upload and
        subsequently waiting for the task completion.
        """
        self.helper.endpoint_id = "source-uuid"
        self.helper.endpoint_path = "/path/to/data"
        self.helper.obj_name = "data"
        self.helper.dir_flag = "-r"

        mock_init_json = json.dumps({"task_id": "transfer-task-123"}).encode("utf-8")

        # Mock sequence: 1. globus transfer initiation, 2. globus task wait
        mock_run.side_effect = [
            (mock_init_json, b"", 0),
            (b"Task completed", b"", 0),
        ]

        self.helper.globus_upload(
            destination_directory="dest-dir",
            destination_endpoint_id="dest-endpoint-uuid",
            entry_reference="entry-123",
        )

        # Validate transfer command construction
        args0, _ = mock_run.call_args_list[0]
        cmd0 = args0[0]
        self.assertEqual(cmd0[0:2], ["globus", "transfer"])
        self.assertIn("-r", cmd0)
        self.assertTrue(any(s.startswith("source-uuid:") for s in cmd0))
        self.assertTrue(any(s.startswith("dest-endpoint-uuid:") for s in cmd0))

        # Validate task wait command construction
        args1, _ = mock_run.call_args_list[1]
        cmd1 = args1[0]
        self.assertEqual(cmd1[0:3], ["globus", "task", "wait"])
        self.assertIn("transfer-task-123", cmd1)

    @patch("empiar_depositor.empiar_depositor.run_shell_command")
    def test_login_failure_raises_clierror(self, mock_run):
        """
        Ensures that a CliError with the specific code 'E_GLOBUS_LOGIN'
        is raised when the Globus CLI returns a non-zero exit status.
        """
        mock_run.return_value = (b"General Failure", b"Invalid credentials", 1)

        with self.assertRaises(CliError) as ctx:
            self.helper.login_and_identify()

        self.assertEqual(ctx.exception.code, "E_GLOBUS_LOGIN")
        self.assertIn("Globus login failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()