import unittest
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import patch


class TestAsperaUpload(unittest.TestCase):
    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_failed_upload(self, mock_popen):
        mock_popen.return_value.stdout.readline.return_value = ''
        mock_popen.return_value.returncode = 1

        empDep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "", entry_id=1, entry_directory='DIR')

        with self.assertRaises(SystemExit) as cm:
            c = empDep.aspera_upload()
        self.assertEqual(cm.exception.args[0], 1)


if __name__ == '__main__':
    unittest.main()
