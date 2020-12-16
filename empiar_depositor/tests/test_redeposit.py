import unittest
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import patch
from empiar_depositor.tests.testutils import EmpiarDepositorTest, capture, mock_response


class TestCreateNewDeposition(EmpiarDepositorTest):
    @patch('empiar_depositor.empiar_depositor.requests.put')
    def test_no_response(self, mock_put):
        mock_put.return_value = None

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.redeposit()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.put')
    def test_unauthorized_stdout(self, mock_put):
        mock_put = mock_response(
            mock_put,
            status_code=401,
            headers={'content-type': 'application/json'},
            json={'detail': 'Invalid token.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        with capture(emp_dep.redeposit) as output:
            self.assertTrue('The update of an EMPIAR deposition was not successful. Returned response:' in output and
                            'Status code: 401' in output)

    @patch('empiar_depositor.empiar_depositor.requests.put')
    def test_unauthorized_return(self, mock_put):
        mock_put = mock_response(
            mock_put,
            status_code=401,
            headers={'content-type': 'application/json'},
            json={'detail': 'Invalid token.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.redeposit()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.put')
    def test_non_int_entry_id_stdout(self, mock_put):
        mock_put = mock_response(
            mock_put,
            headers={'content-type': 'application/json'},
            json={'deposition': True, 'directory': 'DIR', 'entry_id': 'ID'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        with capture(emp_dep.redeposit) as output:
            self.assertTrue('Error occurred while trying to update an EMPIAR deposition. Returned entry id is not an '
                            'integer number' in output)

    @patch('empiar_depositor.empiar_depositor.requests.put')
    def test_non_int_entry_id_return(self, mock_put):
        mock_put = mock_response(
            mock_put,
            headers={'content-type': 'application/json'},
            json={'deposition': True, 'directory': 'DIR', 'entry_id': 'ID'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.redeposit()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.put')
    def test_no_permission_stdout(self, mock_put):
        mock_put = mock_response(
            mock_put,
            status_code=403,
            headers={'content-type': 'application/json'},
            json={'detail': 'You do not have permission to perform this action.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        with capture(emp_dep.redeposit) as output:
            self.assertTrue('The update of an EMPIAR deposition was not successful. Returned response:' in output and
                            'Status code: 403' in output)

    @patch('empiar_depositor.empiar_depositor.requests.put')
    def test_no_permission_return(self, mock_put):
        mock_put = mock_response(
            mock_put,
            status_code=403,
            headers={'content-type': 'application/json'},
            json={'detail': 'You do not have permission to perform this action.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.redeposit()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.put')
    def test_successful_deposition(self, mock_put):
        mock_put = mock_response(
            mock_put,
            headers={'content-type': 'application/json'},
            json={'deposition': True, 'directory': 'DIR', 'entry_id': 1}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")
 
        c = emp_dep.redeposit()
        self.assertEqual(c, 0)


if __name__ == '__main__':
    unittest.main()
