import unittest
import requests
from getpass import getpass

class TestRequests(unittest.TestCase):
    token = getpass(prompt='Token: ')
    headers = {
        'Authorization': 'Token ' + token,
        'Content-Type': 'application/json',
    }

    def test_post_unauthorized(self):
        resp = requests.post('https://wwwdev.ebi.ac.uk/pdbe/emdb/empiar_api/empiar/api/deposit_entry/')
        self.assertEqual(resp.status_code, 401)


    def test_too_many_requests_throttling(self):
        # Has to be run once a minute at most
        for i in xrange(0,11):
            resp = requests.post('https://wwwdev.ebi.ac.uk/pdbe/emdb/empiar_api/empiar/api/deposit_entry/', headers=self.headers, verify=False)

        self.assertEqual(resp.status_code, 429)


if __name__ == '__main__':
    unittest.main()
