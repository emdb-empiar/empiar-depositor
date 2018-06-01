import unittest
from empiar_depositor.empiar_depositor import EmpiarDepositor
from mock import Mock, patch
from requests.models import Response


class TestThumbnailUpload(unittest.TestCase):
    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_response(self, mock_post):
        mock_post.return_value = None

        empDep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "", entry_thumbnail="tests/img/entry_thumbnail.gif")

        with self.assertRaises(SystemExit) as cm:
            c = empDep.thumbnail_upload()
        self.assertEqual(cm.exception.args[0], 1)

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_no_permission(self, mock_post):
        mock_post.return_value = Mock(ok=True, spec=Response)
        mock_post.return_value.status_code = 403
        mock_post.return_value.json.return_value = {'detail': 'You do not have permission to perform this action.'}
  
        empDep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "", entry_thumbnail="tests/img/entry_thumbnail.gif")
  
        with self.assertRaises(SystemExit) as cm:
            c = empDep.thumbnail_upload()
        self.assertTrue('The upload of the thumbnail for EMPIAR deposition was not successful. Returned response:' in cm.exception.args[0] and 'Status code: 403' in cm.exception.args[0])

    @patch('empiar_depositor.empiar_depositor.requests.post')
    def test_successful_upload(self, mock_post):
        mock_post.return_value = Mock(ok=True, spec=Response)
        mock_post.return_value.json.return_value = {'thumbnail_upload': True}

        empDep = EmpiarDepositor("ABC123", "tests/deposition_json/working_example.json", "", "", entry_thumbnail="tests/img/entry_thumbnail.gif")
  
        c = empDep.thumbnail_upload()
        self.assertEqual(c, 0)


if __name__ == '__main__':
    unittest.main()
