import unittest
from empiar_depositor.empiar_depositor import main as empiar_depositor_main
from mock import patch
from empiar_depositor.tests.testutils import capture, EmpiarDepositorTest


class TestMain(EmpiarDepositorTest):
    def test_json_input_does_not_exist(self, ):
        with capture(empiar_depositor_main, ["ABC123", "THIS DOES NOT EXIST", ""]) as output:
            self.assertEqual(output, 'The specified JSON file does not exist\n')

    def test_json_input_does_exists(self):
        with capture(empiar_depositor_main, ["ABC123", self.json_path, ""]) as output:
            self.assertNotEqual(output, 'The specified JSON file does not exist\n')

    def test_ascp_does_not_exist(self):
        with capture(empiar_depositor_main, ["ABC123", self.json_path, "", "-aascp",
                                             "-ppassword"]) as output:
            self.assertEqual(output, "The specified Aspera executable does not exist\n")

    def test_wrong_aspera_executable(self):
        with capture(empiar_depositor_main, ["ABC123", self.json_path,
                                             "-a" + self.thumbnail_path,
                                             "img/entry_thumbnail.gif",
                                             "-ppassword"]) as output:
            self.assertTrue("Please specify the correct path to ascp executable" in output)

    @patch('empiar_depositor.empiar_depositor.os.path.isfile')
    def test_aspera_does_not_work(self, mock_isfile):
        mock_isfile.return_value = True
        with capture(empiar_depositor_main, ["ABC123", self.json_path,
                                             "-aascp.exe", "img/entry_thumbnail.gif",
                                             "-ppassword"]) as output:
            self.assertTrue("The specified ascp does not work." in output)

    @patch('empiar_depositor.empiar_depositor.os.path.isfile')
    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_aspera_does_work_globus_login_does_not(self, mock_popen, mock_isfile):
        mock_isfile.return_value = True

        mock_popen.return_value.communicate.return_value = (b'Usage: ascp', b'')
        mock_popen.return_value.returncode = 112

        with capture(empiar_depositor_main, ["ABC123", self.json_path,
                                             "-aascp.exe", "img/entry_thumbnail.gif",
                                             "-ppassword", "-gtest"]) as output:
            self.assertTrue("Logging in to Globus...\nError while logging in into Globus" in output)


if __name__ == '__main__':
    unittest.main()
