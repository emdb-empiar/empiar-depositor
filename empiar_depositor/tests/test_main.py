import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestMain(unittest.TestCase):
    """
    Integration-level tests for the empiar_depositor CLI main function.
    These tests verify the end-to-end workflow by mocking the primary
    functional classes (GlobusHelper and EmpiarDepositor).
    """

    @patch("empiar_depositor.empiar_depositor.load_json_file")
    @patch("empiar_depositor.empiar_depositor.validate_empiar_json", return_value=True)
    @patch("empiar_depositor.empiar_depositor.Path.is_file", return_value=True)
    @patch("empiar_depositor.empiar_depositor.GlobusHelper")
    @patch("empiar_depositor.empiar_depositor.EmpiarDepositor")
    @patch("empiar_depositor.empiar_depositor.argparse.ArgumentParser.parse_args")
    def test_main_happy_path_submits(
        self,
        mock_parse_args,
        mock_dep_cls,
        mock_globus_cls,
        mock_path_is_file,
        mock_validate_json,
        mock_load_json_file,
    ):
        """
        Tests the standard successful workflow where metadata is valid,
        Globus transfer completes, and the entry is successfully submitted.
        """
        from empiar_depositor.empiar_depositor import main

        # Simulate standard CLI arguments for a successful run
        mock_parse_args.return_value = SimpleNamespace(
            verbose=1,
            user=None,
            password=None,
            token="mock-token",
            json_path="metadata.json",
            thumbnail="thumb.png",
            endpoint="test-endpoint",
            data_path="/path/to/data",
            force_login=False,
            production=False,
            destination_endpoint_id=None,
            grant_rights_usernames=None,
            grant_rights_emails=None,
            grant_rights_orcids=None,
            resume=None,
            stop_submit=False,
            ignore_certificate=False,
            request_timeout=200,
            log_file=None,
        )

        # main() loads metadata + schema via load_json_file
        mock_load_json_file.side_effect = [
            {"entry": "data"},          # metadata.json
            {"type": "object"},         # empiar_deposition.schema.json
        ]

        # Configure Globus mock behavior
        mock_globus = mock_globus_cls.return_value
        mock_globus.validate_globus_details.return_value = None
        mock_globus.endpoint_id = "source-uuid"
        mock_globus.user_identity = "user@globus"
        mock_globus.globus_upload.return_value = None

        # Configure Depositor mock behavior
        mock_dep = mock_dep_cls.return_value
        mock_dep.create_new_deposition.return_value = None
        mock_dep.redeposit.return_value = None
        mock_dep.thumbnail_upload.return_value = None
        mock_dep.grant_rights.return_value = None
        mock_dep.share_upload_directory.return_value = None
        mock_dep.submit_deposition.return_value = None

        mock_dep.entry_id = "123"
        mock_dep.entry_directory = "dir-abc"
        mock_dep.empiar_accession = "EMPIAR-10001"

        # Suppress printed output during test execution
        with patch("sys.stdout", new=io.StringIO()):
            main()

        # Verify the sequence of calls
        mock_globus.validate_globus_details.assert_called_once()
        mock_dep.create_new_deposition.assert_called_once()
        mock_dep.share_upload_directory.assert_called_once()
        mock_globus.globus_upload.assert_called_once()
        mock_dep.submit_deposition.assert_called_once()

    @patch("empiar_depositor.empiar_depositor.load_json_file")
    @patch("empiar_depositor.empiar_depositor.validate_empiar_json", return_value=True)
    @patch("empiar_depositor.empiar_depositor.Path.is_file", return_value=True)
    @patch("empiar_depositor.empiar_depositor.GlobusHelper")
    @patch("empiar_depositor.empiar_depositor.EmpiarDepositor")
    @patch("empiar_depositor.empiar_depositor.argparse.ArgumentParser.parse_args")
    def test_main_stop_submit_skips_submission(
        self,
        mock_parse_args,
        mock_dep_cls,
        mock_globus_cls,
        mock_path_is_file,
        mock_validate_json,
        mock_load_json_file,
    ):
        """
        Tests that the script respects the --stop-submit flag by completing
        the upload but skipping the final API submission step.
        """
        from empiar_depositor.empiar_depositor import main

        mock_parse_args.return_value = SimpleNamespace(
            verbose=1,
            user=None,
            password=None,
            token="mock-token",
            json_path="metadata.json",
            thumbnail="thumb.png",
            endpoint="test-endpoint",
            data_path="/path/to/data",
            force_login=False,
            production=False,
            destination_endpoint_id=None,
            grant_rights_usernames=None,
            grant_rights_emails=None,
            grant_rights_orcids=None,
            resume=None,
            stop_submit=True,  # User explicitly requested no submission
            ignore_certificate=False,
            request_timeout=200,
            log_file=None,
        )

        mock_load_json_file.side_effect = [
            {"entry": "data"},          # metadata.json
            {"type": "object"},         # empiar_deposition.schema.json
        ]

        mock_globus = mock_globus_cls.return_value
        mock_globus.validate_globus_details.return_value = None
        mock_globus.endpoint_id = "source-uuid"
        mock_globus.user_identity = "user@globus"
        mock_globus.globus_upload.return_value = None

        mock_dep = mock_dep_cls.return_value
        mock_dep.create_new_deposition.return_value = None
        mock_dep.share_upload_directory.return_value = None

        mock_dep.entry_id = "123"
        mock_dep.entry_directory = "dir-abc"
        mock_dep.empiar_accession = None

        with patch("sys.stdout", new=io.StringIO()):
            main()

        # Upload should happen, but submission should be bypassed
        mock_dep.create_new_deposition.assert_called_once()
        mock_globus.globus_upload.assert_called_once()
        mock_dep.submit_deposition.assert_not_called()

    @patch("empiar_depositor.empiar_depositor.load_json_file")
    @patch("empiar_depositor.empiar_depositor.validate_empiar_json", return_value=False)
    @patch("empiar_depositor.empiar_depositor.Path.is_file", return_value=True)
    @patch("empiar_depositor.empiar_depositor.GlobusHelper")
    @patch("empiar_depositor.empiar_depositor.EmpiarDepositor")
    @patch("empiar_depositor.empiar_depositor.argparse.ArgumentParser.parse_args")
    def test_main_schema_validation_failure_stops_early(
        self,
        mock_parse_args,
        mock_dep_cls,
        mock_globus_cls,
        mock_path_is_file,
        mock_validate_json,
        mock_load_json_file,
    ):
        """
        Verifies that the script terminates immediately if the metadata
        JSON fails schema validation, preventing unnecessary API or Globus calls.
        """
        from empiar_depositor.empiar_depositor import main, CliError

        mock_parse_args.return_value = SimpleNamespace(
            verbose=1,
            user=None,
            password=None,
            token="mock-token",
            json_path="metadata.json",
            thumbnail="thumb.png",
            endpoint="test-endpoint",
            data_path="/path/to/data",
            force_login=False,
            production=False,
            destination_endpoint_id=None,
            grant_rights_usernames=None,
            grant_rights_emails=None,
            grant_rights_orcids=None,
            resume=None,
            stop_submit=False,
            ignore_certificate=False,
            request_timeout=200,
            log_file=None,
        )

        mock_load_json_file.side_effect = [
            {"entry": "data"},          # metadata.json
            {"type": "object"},         # empiar_deposition.schema.json
        ]

        with patch("sys.stdout", new=io.StringIO()):
            with self.assertRaises(CliError) as cm:
                main()

        self.assertEqual(cm.exception.code, "E_SCHEMA")

        # Assert that primary logic classes were never instantiated
        mock_globus_cls.assert_not_called()
        mock_dep_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()