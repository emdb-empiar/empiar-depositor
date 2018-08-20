import unittest
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import patch


class TestAsperaUpload(unittest.TestCase):
    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_failed_upload(self, mock_popen):
        mock_popen.return_value.stdout.readline.return_value = b''
        mock_popen.return_value.returncode = 1

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "ascp", entry_id=1,
                                  entry_directory='DIR')

        c = emp_dep.aspera_upload()
        self.assertEqual(c, 1)


if __name__ == '__main__':
    unittest.main()
