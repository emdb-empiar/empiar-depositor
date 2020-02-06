import unittest
import requests
from empiar_depositor.empiar_depositor import EmpiarDepositor
from empiar_depositor.tests.testutils import EmpiarDepositorTest
from mock import patch


class TestMakeResponse(EmpiarDepositorTest):
    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_response_token_auth(self, mock_post):
        mock_post.return_value = None

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.make_request(requests.post)
        self.assertEqual(c, None)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_response_basic_auth(self, mock_post):
        mock_post.return_value = None

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "", password='12345')

        c = emp_dep.make_request(requests.post)
        self.assertEqual(c, None)


if __name__ == '__main__':
    unittest.main()
