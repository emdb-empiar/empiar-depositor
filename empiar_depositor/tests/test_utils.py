import io
import unittest
from unittest.mock import patch, MagicMock, mock_open
from requests.models import Response

from empiar_depositor.empiar_depositor import (
    CliError,
    _ensure,
    run_shell_command,
    check_json_response,
    validate_empiar_json,
)


class TestUtilities(unittest.TestCase):
    """
    Unit tests for the helper functions and utility classes used by the
    EMPIAR depositor, including command execution and response validation.
    """

    def test_clierror_str(self):
        """
        Verifies that the CliError custom exception formats its string
        representation correctly with the error code, step, and detail.
        """
        e = CliError(code="E1", step="step1", message="oops", detail="more")
        s = str(e)
        self.assertIn("[E1] (step1) oops", s)
        self.assertIn("more", s)

    def test_ensure_raises(self):
        """
        Tests the _ensure helper to verify it correctly raises a CliError
        when the condition is False.
        """
        with self.assertRaises(CliError) as ctx:
            _ensure(False, code="E_FAIL", step="x", message="nope", detail="d")
        self.assertEqual(ctx.exception.code, "E_FAIL")

    @patch("empiar_depositor.empiar_depositor.subprocess.Popen")
    def test_run_shell_command_success(self, mock_popen):
        """
        Tests the successful execution of a shell command using subprocess,
        ensuring stdout and exit codes are captured correctly.
        """
        proc = MagicMock()
        proc.communicate.return_value = (b"out", b"")
        proc.returncode = 0
        mock_popen.return_value = proc

        out, err, code = run_shell_command(["echo", "hi"])
        self.assertEqual(out, b"out")
        self.assertEqual(code, 0)

    @patch("empiar_depositor.empiar_depositor.subprocess.Popen", side_effect=FileNotFoundError())
    def test_run_shell_command_command_not_found(self, mock_popen):
        """
        Tests the error handling when a shell command (like globus-cli)
        is missing from the system path.
        """
        out, err, code = run_shell_command(["globus", "whoami"])
        self.assertEqual(code, 127)
        self.assertIn(b"globus-cli", err)

    def test_check_json_response_accepts_json(self):
        """
        Confirms that check_json_response identifies 'application/json'
        content-type correctly.
        """
        res = MagicMock(spec=Response)
        res.headers = {"content-type": "application/json"}
        self.assertTrue(check_json_response(res))

    def test_check_json_response_rejects_non_json(self):
        """
        Confirms that check_json_response correctly rejects non-JSON
        content-types like HTML.
        """
        res = MagicMock(spec=Response)
        res.headers = {"content-type": "text/html"}
        self.assertFalse(check_json_response(res))

    @patch("empiar_depositor.empiar_depositor.Path.exists", return_value=False)
    def test_validate_empiar_json_schema_missing_returns_true(self, mock_exists):
        """
        Tests that JSON validation gracefully skips and returns True if the
        schema file is not found, logging a warning instead of failing.
        """
        logger = MagicMock()
        ok = validate_empiar_json("in.json", "schema.json", logger)
        self.assertTrue(ok)
        logger.warning.assert_called()

    @patch("empiar_depositor.empiar_depositor.Path.exists", return_value=True)
    @patch("empiar_depositor.empiar_depositor.validate")
    def test_validate_empiar_json_success(self, mock_validate, mock_exists):
        """
        Tests a successful metadata validation scenario where both the schema
        and input JSON are valid.
        """
        logger = MagicMock()
        m_open = mock_open()
        # Mocking sequential opens: first for the schema, second for the input file
        m_open.side_effect = [
            mock_open(read_data='{"type": "object"}').return_value,
            mock_open(read_data='{"entry": "data"}').return_value,
        ]
        with patch("builtins.open", m_open):
            ok = validate_empiar_json("in.json", "schema.json", logger)
        self.assertTrue(ok)
        mock_validate.assert_called_once()

    @patch("empiar_depositor.empiar_depositor.Path.exists", return_value=True)
    def test_validate_empiar_json_invalid_json_returns_false(self, mock_exists):
        """
        Ensures that validation returns False and logs an exception if the
        input file contains malformed JSON.
        """
        logger = MagicMock()
        m_open = mock_open()
        m_open.side_effect = [
            mock_open(read_data='{"type": "object"}').return_value,
            mock_open(read_data="{bad json").return_value,
        ]
        with patch("builtins.open", m_open):
            ok = validate_empiar_json("in.json", "schema.json", logger)
        self.assertFalse(ok)
        logger.exception.assert_called()


if __name__ == "__main__":
    unittest.main()