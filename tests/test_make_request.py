import unittest
import requests
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import patch


class TestMakeResponse(unittest.TestCase):
    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_response_token_auth(self, mock_post):
        mock_post.return_value = None

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "")

        c = emp_dep.make_request(requests.post)
        self.assertEqual(c, None)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_response_basic_auth(self, mock_post):
        mock_post.return_value = None

        emp_dep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", password='12345')

        c = emp_dep.make_request(requests.post)
        self.assertEqual(c, None)


if __name__ == '__main__':
    unittest.main()
