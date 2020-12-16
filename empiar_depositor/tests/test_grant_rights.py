import unittest
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import patch
from empiar_depositor.tests.testutils import EmpiarDepositorTest, capture, mock_response


class TestGrantRights(EmpiarDepositorTest):
    grant_rights_usernames = 'test1:2,test2:3'
    grant_rights_emails = 'test3@test.com:2,test4@test.com:3'
    grant_rights_orcids = '0000-0000-0000-0000:2,0000-0000-0000-0001:3'

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_entry_id_stdout(self, mock_post):
        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        with capture(emp_dep.grant_rights) as output:
            self.assertTrue('Please provide an entry ID.' in output)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_entry_id_return(self, mock_post):
        emp_dep = EmpiarDepositor("ABC123", self.json_path, "")

        c = emp_dep.grant_rights()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_response(self, mock_post):
        mock_post.return_value = None

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "", entry_id=1)

        c = emp_dep.grant_rights()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_rights_granting_input_stdout(self, mock_post):
        mock_post = mock_response(
            mock_post,
            status_code=403,
            headers={'content-type': 'application/json'},
            json={'detail': 'You do not have permission to perform this action.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "", entry_id=1)

        with capture(emp_dep.grant_rights) as output:
            self.assertTrue('The granting rights for EMPIAR deposition was not successful.' in output)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_rights_granting_input_return(self, mock_post):
        mock_post = mock_response(
            mock_post,
            status_code=403,
            headers={'content-type': 'application/json'},
            json={'detail': 'You do not have permission to perform this action.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "", entry_id=1)

        c = emp_dep.grant_rights()
        self.assertEqual(c, 1)



    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_permission_stdout(self, mock_post):
        mock_post = mock_response(
            mock_post,
            status_code=403,
            headers={'content-type': 'application/json'},
            json={'detail': 'You do not have permission to perform this action.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "", entry_id=1,
                                  grant_rights_usernames=self.grant_rights_usernames)

        with capture(emp_dep.grant_rights) as output:
            self.assertTrue('You do not have permission to perform this action.' in output and
                            'Status code: 403' in output)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_permission_return(self, mock_post):
        mock_post = mock_response(
            mock_post,
            status_code=403,
            headers={'content-type': 'application/json'},
            json={'detail': 'You do not have permission to perform this action.'}
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "", entry_id=1,
                                  grant_rights_usernames=self.grant_rights_usernames)

        c = emp_dep.grant_rights()
        self.assertEqual(c, 1)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_successful_rights_granting(self, mock_post):
        mock_post = mock_response(
            mock_post,
            status_code=200,
            headers={'content-type': 'application/json'},
            json={
                'test1': True,'test2': True,
                'test3@test.com': True, 'test4@test.com': True,
                '0000-0000-0000-0000': True, '0000-0000-0000-0001': True
            }
        )

        emp_dep = EmpiarDepositor("ABC123", self.json_path, "",
                                  entry_id = 1,
                                  grant_rights_usernames=self.grant_rights_usernames,
                                  grant_rights_emails=self.grant_rights_emails,
                                  grant_rights_orcids=self.grant_rights_orcids
                                  )

        c = emp_dep.grant_rights()
        self.assertEqual(c, 0)


if __name__ == '__main__':
    unittest.main()
