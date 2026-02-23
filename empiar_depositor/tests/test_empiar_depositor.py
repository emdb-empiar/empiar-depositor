import unittest
import json
from unittest.mock import patch, MagicMock, mock_open
from requests import Response

from empiar_depositor.empiar_depositor import EmpiarDepositor, CliError


class TestEmpiarDepositor(unittest.TestCase):
    """
    Unit tests for the EmpiarDepositor class focusing on API interactions,
    polling mechanisms, and error handling.
    """

    def setUp(self):
        """
        Sets up a mock environment and an EmpiarDepositor instance before each test.
        """
        self.log = MagicMock()

        self.params = {
            "empiar_token": "mock-token",
            "json_input": "metadata.json",
            "server_root": "https://www.ebi.ac.uk",
            "data": "/mock/data",
            "globus_source_endpoint": "endpoint-uuid",
            "ignore_certificate": True,
            "entry_thumbnail": "thumb.png",
            "log": self.log,
        }
        self.depositor = EmpiarDepositor(**self.params)

    @patch("empiar_depositor.empiar_depositor.check_json_response", return_value=True)
    @patch("empiar_depositor.empiar_depositor.time.sleep", return_value=None)
    @patch("empiar_depositor.empiar_depositor.EmpiarDepositor.make_request")
    def test_create_new_deposition_with_polling(self, mock_make_request, mock_sleep, mock_check_json):
        """
        Tests the creation of a new deposition, ensuring the script correctly handles
        polling when the server returns an 'In progress' status for the upload directory.
        """
        # Mock POST response for initial deposition creation
        mock_post_res = MagicMock(spec=Response)
        mock_post_res.ok = True
        mock_post_res.status_code = 201
        mock_post_res.headers = {"content-type": "application/json"}
        mock_post_res.text = ""
        mock_post_res.json.return_value = {
            "deposition": True,
            "entry_id": "12345",
            "directory": "In progress",
        }

        # Mock GET response for polling fetch_entry_upload_directory
        mock_get_res = MagicMock(spec=Response)
        mock_get_res.ok = True
        mock_get_res.status_code = 200
        mock_get_res.headers = {"content-type": "application/json"}
        mock_get_res.text = ""
        mock_get_res.json.return_value = {
            "status": "Completed",
            "return_value": "final_empiar_directory_path",
        }

        mock_make_request.side_effect = [mock_post_res, mock_get_res]

        with patch("builtins.open", mock_open(read_data=b"{}")):
            self.depositor.create_new_deposition()

        self.assertEqual(self.depositor.entry_id, "12345")
        self.assertEqual(self.depositor.entry_directory, "final_empiar_directory_path")
        self.assertEqual(mock_make_request.call_count, 2)

    @patch("empiar_depositor.empiar_depositor.EmpiarDepositor.make_request")
    def test_share_upload_directory_success(self, mock_make_request):
        """
        Verifies that the Globus upload directory sharing logic correctly parses
        the nested JSON string response from the server.
        """
        self.depositor.entry_id = "12345"
        self.depositor.globus_local_username = "test_user"

        mock_response = MagicMock(spec=Response)
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = ""

        # The API currently returns a JSON-encoded string within the JSON response
        inner_data = {"response": ["1", "Success"]}
        mock_response.json.return_value = json.dumps(inner_data)

        mock_make_request.return_value = mock_response

        # Should execute without raising exceptions
        self.depositor.share_upload_directory()

        self.assertEqual(mock_make_request.call_count, 1)

    @patch("empiar_depositor.empiar_depositor.check_json_response", return_value=True)
    @patch("empiar_depositor.empiar_depositor.EmpiarDepositor.make_request")
    def test_thumbnail_upload_failure_raises_clierror(self, mock_make_request, mock_check_json):
        """
        Ensures that a CliError is raised if the thumbnail upload fails
        at the application level (e.g., upload flag is False).
        """
        self.depositor.entry_id = "12345"
        self.depositor.entry_thumbnail = "thumb.png"

        mock_response = MagicMock(spec=Response)
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = ""
        mock_response.json.return_value = {"thumbnail_upload": False}

        mock_make_request.return_value = mock_response

        with patch("builtins.open", mock_open(read_data=b"fake-image-binary")):
            with self.assertRaises(CliError) as ctx:
                self.depositor.thumbnail_upload()

        self.assertEqual(ctx.exception.code, "E_API_THUMBNAIL")

    def test_prepare_rights_data(self):
        """
        Validates the parsing logic for the user rights string input.
        """
        input_data = "user1:1,user2:2"
        expected = {"user1": "1", "user2": "2"}
        result = self.depositor.prepare_rights_data(input_data)
        self.assertEqual(result, expected)

    @patch("empiar_depositor.empiar_depositor.check_json_response", return_value=True)
    @patch("empiar_depositor.empiar_depositor.time.sleep", return_value=None)
    @patch("empiar_depositor.empiar_depositor.EmpiarDepositor.make_request")
    def test_submit_deposition_with_polling(self, mock_make_request, mock_sleep, mock_check_json):
        """
        Tests the submission workflow, including multi-step polling until
        the EMPIAR accession ID is successfully retrieved.
        """
        self.depositor.entry_id = "12345"

        # Mock POST response for initial submission request
        mock_post_res = MagicMock(spec=Response)
        mock_post_res.ok = True
        mock_post_res.status_code = 201
        mock_post_res.headers = {"content-type": "application/json"}
        mock_post_res.text = ""
        mock_post_res.json.return_value = {"submission": True}

        # First poll response: status is still in progress
        res_poll_1 = MagicMock(spec=Response)
        res_poll_1.ok = True
        res_poll_1.status_code = 200
        res_poll_1.headers = {"content-type": "application/json"}
        res_poll_1.text = ""
        res_poll_1.json.return_value = {
            "status": "In progress",
            "submission": True,
            "empiar_id": "",
            "entry_id": "12345",
        }

        # Second poll response: status is completed
        res_poll_2 = MagicMock(spec=Response)
        res_poll_2.ok = True
        res_poll_2.status_code = 200
        res_poll_2.headers = {"content-type": "application/json"}
        res_poll_2.text = ""
        res_poll_2.json.return_value = {
            "status": "Completed",
            "submission": True,
            "return_value": "EMPIAR-10001",
            "entry_id": "12345",
        }

        # Sequence: Initiate submission -> Poll 1 (waiting) -> Poll 2 (done)
        mock_make_request.side_effect = [mock_post_res, res_poll_1, res_poll_2]

        self.depositor.submit_deposition()

        self.assertEqual(self.depositor.empiar_accession, "EMPIAR-10001")
        self.assertEqual(mock_make_request.call_count, 3)


if __name__ == "__main__":
    unittest.main()