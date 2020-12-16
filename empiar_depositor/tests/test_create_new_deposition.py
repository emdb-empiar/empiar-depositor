import unittest
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import patch
from empiar_depositor.tests.testutils import EmpiarDepositorTest, capture, mock_response


class TestCreateNewDeposition(EmpiarDepositorTest):
    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_response(self, mock_post):
        mock_post.return_value = None

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.create_new_deposition()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_unauthorized_stdout(self, mock_post):
        mock_post = mock_response(
            mock_post,
            status_code=401,
            headers={'content-type': 'application/json'},
            json={'detail': 'Invalid token.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        with capture(emp_dep.create_new_deposition) as output:
            self.assertTrue('The creation of an EMPIAR deposition was not successful. Returned response:' in
                            output and 'Status code: 401' in output)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_unauthorized_return(self, mock_post):
        mock_post = mock_response(
            mock_post,
            status_code=401,
            headers={'content-type': 'application/json'},
            json={'detail': 'Invalid token.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.create_new_deposition()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_non_int_entry_id_stdout(self, mock_post):
        mock_post = mock_response(
            mock_post,
            headers={'content-type': 'application/json'},
            json={'deposition': True, 'directory': 'DIR', 'entry_id': 'ID'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        with capture(emp_dep.create_new_deposition) as output:
            self.assertTrue('Error occurred while trying to create an EMPIAR deposition. Returned entry id is not an '
                            'integer number' in output)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_non_int_entry_id_return(self, mock_post):
        mock_post = mock_response(
            mock_post,
            headers={'content-type': 'application/json'},
            json={'deposition': True, 'directory': 'DIR', 'entry_id': 'ID'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.create_new_deposition()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_successful_deposition(self, mock_post):
        mock_post = mock_response(
            mock_post,
            headers={'content-type': 'application/json'},
            json={'deposition': True, 'directory': 'DIR', 'entry_id': 1}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")
 
        c = emp_dep.create_new_deposition()
        self.assertEqual(c, 0)


if __name__ == '__main__':
    unittest.main()
