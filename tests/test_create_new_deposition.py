import unittest
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import Mock, patch
from requests.models import Response


class TestCreateNewDeposition(unittest.TestCase):
    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_response(self, mock_post):
        mock_post.return_value = None

        empDep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "")

        with self.assertRaises(SystemExit) as cm:
            c = empDep.create_new_deposition()
        self.assertEqual(cm.exception.args[0], 1)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_unauthorized(self, mock_post):
        mock_post.return_value = Mock(ok=True, spec=Response)
        mock_post.return_value.status_code = 401
        mock_post.return_value.json.return_value = {'detail': 'Invalid token.'}
 
        empDep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "")
 
        with self.assertRaises(SystemExit) as cm:
            c = empDep.create_new_deposition()
        self.assertTrue('The creation of an EMPIAR deposition was not successful. Returned response:' in cm.exception.args[0] and 'Status code: 401' in cm.exception.args[0])

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_non_int_entry_id(self, mock_post):
        mock_post.return_value = Mock(ok=True, spec=Response)
        mock_post.return_value.json.return_value = {'deposition': True, 'directory': 'DIR', 'entry_id': 'ID'}

        empDep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "")
 
        with self.assertRaises(SystemExit) as cm:
            c = empDep.create_new_deposition()
        self.assertTrue('Error occurred while trying to create an EMPIAR deposition. Returned entry id is not an integer number' in cm.exception.args[0])

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_successful_deposition(self, mock_post):
        mock_post.return_value = Mock(ok=True, spec=Response)
        mock_post.return_value.json.return_value = {'deposition': True, 'directory': 'DIR', 'entry_id': 1}

        empDep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "")
 
        c = empDep.create_new_deposition()
        self.assertEqual(c, 0)


if __name__ == '__main__':
    unittest.main()
