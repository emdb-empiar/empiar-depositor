import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
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
        self.assertEqual(ctx.exception.step, "x")
        self.assertIn("nope", str(ctx.exception))

    @patch("empiar_depositor.empiar_depositor.subprocess.Popen")
    def test_run_shell_command_success(self, mock_popen):
        """
        Tests the successful execution of a shell command using subprocess,
        ensuring stdout and exit codes are captured correctly.
        """
        proc = MagicMock()
        proc.communicate.return_value = (b"out", None)
        proc.returncode = 0
        mock_popen.return_value = proc

        out, err, code = run_shell_command(["echo", "hi"])
        self.assertEqual(out, b"out")
        self.assertIsNone(err)
        self.assertEqual(code, 0)

    @patch("empiar_depositor.empiar_depositor.subprocess.Popen", side_effect=FileNotFoundError())
    def test_run_shell_command_command_not_found(self, mock_popen):
        """
        Tests the error handling when a shell command (like globus-cli)
        is missing from the system path.
        """
        out, err, code = run_shell_command(["globus", "whoami"])
        self.assertEqual(out, b"")
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

    def test_check_json_response_accepts_json_with_charset(self):
        """
        Confirms that check_json_response correctly asserts JSON
        content-types
        """
        res = Response()
        res.headers = {"content-type": "application/json; charset=utf-8"}
        self.assertTrue(check_json_response(res))

    def test_check_json_response_rejects_non_json(self):
        """
        Confirms that check_json_response correctly rejects non-JSON
        content-types like HTML.
        """
        res = MagicMock(spec=Response)
        res.headers = {"content-type": "text/html"}
        self.assertFalse(check_json_response(res))

    def test_check_json_response_rejects_non_response_object(self):
        """
        Confirms that check_json_response correctly rejects non-JSON
        """
        self.assertFalse(check_json_response({"headers": {"content-type": "application/json"}}))

    @patch("empiar_depositor.empiar_depositor.validate")
    def test_validate_empiar_json_success(self, mock_validate):
        """
        validate_empiar_json should return True when jsonschema.validate succeeds.
        """
        logger = MagicMock()
        ok = validate_empiar_json({"a": 1}, {"type": "object"}, logger)
        self.assertTrue(ok)
        mock_validate.assert_called_once()
        logger.info.assert_called()  # "JSON schema validation successful.\n"

    @patch("empiar_depositor.empiar_depositor.validate")
    def test_validate_empiar_json_validation_error_returns_false(self, mock_validate):
        """
        validate_empiar_json should return False and log an error on schema ValidationError.
        """
        class FakeValidationError(Exception):
            def __init__(self, message):
                self.message = message

        logger = MagicMock()

        with patch(
            "empiar_depositor.empiar_depositor.exceptions",
            new=SimpleNamespace(ValidationError=FakeValidationError),
        ):
            mock_validate.side_effect = FakeValidationError("bad field")
            ok = validate_empiar_json({"a": 1}, {"type": "object"}, logger)

        self.assertFalse(ok)
        logger.error.assert_called()  # it logs the formatted validation error

    @patch("empiar_depositor.empiar_depositor.validate")
    def test_validate_empiar_json_json_decode_error_returns_false(self, mock_validate):
        """validate_empiar_json should return False and log exception on JSONDecodeError."""
        logger = MagicMock()
        mock_validate.side_effect = json.JSONDecodeError("msg", doc="{}", pos=1)

        ok = validate_empiar_json({"a": 1}, {"type": "object"}, logger)

        self.assertFalse(ok)
        logger.exception.assert_called()

    @patch("empiar_depositor.empiar_depositor.validate")
    def test_validate_empiar_json_unexpected_error_returns_false(self, mock_validate):
        """validate_empiar_json should return False and log exception on any unexpected error."""
        logger = MagicMock()
        logger = MagicMock()
        mock_validate.side_effect = RuntimeError("boom")

        ok = validate_empiar_json({"a": 1}, {"type": "object"}, logger)

        self.assertFalse(ok)
        logger.exception.assert_called()


if __name__ == "__main__":
    unittest.main()