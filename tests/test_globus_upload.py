import unittest
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import patch
from testutils import capture

missing_id_json_str = """{
  "DATA_TYPE": "transfer_result",
  "code": "Accepted",
  "message": "The transfer has been accepted and a task has been created and queued for execution",
  "request_id": "abc",
  "resource": "/transfer",
  "submission_id": "Task123",
  "task_link": {
    "DATA_TYPE": "link",
    "href": "task/Task123?format=json",
    "rel": "related",
    "resource": "task",
    "title": "related task"
  }
}"""


class TestGlobusUpload(unittest.TestCase):
    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_failed_init_stdout(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ("Task ID: 123", "")
        mock_popen.return_value.returncode = 1

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "globus_obj", "", "globusid",
                                  {"is_dir": False, "obj_name": "globus_obj"}, entry_id=1, entry_directory="entry_dir")

        with capture(emp_dep.globus_upload) as output:
            self.assertTrue('Globus transfer initiation was not successful. Return code:' in output)

    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_failed_init_return(self, mock_popen):
        mock_popen.return_value.communicate.return_value = (None, None)
        mock_popen.return_value.returncode = 1

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "globus_obj", "", "globusid",
                                  {"is_dir": False, "obj_name": "globus_obj"}, entry_id=1, entry_directory="entry_dir")

        c = emp_dep.globus_upload()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_invalid_json_stdout(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ("The transfer has been accepted and a task has been created"
                                                            " and queued for execution. Task ID: 123", None)
        mock_popen.return_value.returncode = 0

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "globus_obj", "", "globusid",
                                  {"is_dir": False, "obj_name": "globus_obj"}, entry_id=1, entry_directory="entry_dir")

        c = emp_dep.globus_upload()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_invalid_json_return(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ("The transfer has been accepted and a task has been created"
                                                            " and queued for execution. Task ID: 123", None)
        mock_popen.return_value.returncode = 0

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "globus_obj", "", "globusid",
                                  {"is_dir": False, "obj_name": "globus_obj"}, entry_id=1, entry_directory="entry_dir")

        with capture(emp_dep.globus_upload) as output:
            self.assertTrue('Error while processing transfer initiation result - the string does not contain a valid '
                            'JSON. Return code' in output)

    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_missing_id_json_stdout(self, mock_popen):
        mock_popen.return_value.communicate.return_value = (missing_id_json_str, None)
        mock_popen.return_value.returncode = 0

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "globus_obj", "", "globusid",
                                  {"is_dir": False, "obj_name": "globus_obj"}, entry_id=1, entry_directory="entry_dir")

        c = emp_dep.globus_upload()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_missing_id_json_return(self, mock_popen):
        mock_popen.return_value.communicate.return_value = (missing_id_json_str, None)
        mock_popen.return_value.returncode = 0

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "globus_obj", "", "globusid",
                                  {"is_dir": False, "obj_name": "globus_obj"}, entry_id=1, entry_directory="entry_dir")

        with capture(emp_dep.globus_upload) as output:
            self.assertTrue('Globus JSON transfer initiation result does not have a valid structure of '
                            'JSON[\'task_id\']. Return code:' in output)

    @patch('empiar_depositor.empiar_depositor.subprocess.Popen')
    def test_failed_wait_upload(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ("Waiting", None)
        mock_popen.return_value.stdout.readline.return_value = b''
        mock_popen.return_value.returncode = 1

        task_id = "Task123"

        c = EmpiarDepositor.globus_upload_wait(task_id)
        self.assertEqual(c, 1)


if __name__ == '__main__':
    unittest.main()
