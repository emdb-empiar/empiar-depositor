import os
import json
import time
import sys
import argparse
import subprocess
import requests
from getpass import getpass
from requests.auth import HTTPBasicAuth
from requests.models import Response


def run_shell_command(command):
    """Run shell command and return output and code."""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p_out, p_err = process.communicate()
    return p_out, p_err, process.returncode


def check_json_response(response):
    """Check if the response has JSON content type."""
    if not isinstance(response, Response):
        return False
    return 'application/json' in response.headers.get('content-type', '').lower()


class EmpiarDepositor:
    def __init__(self, empiar_token, json_input, data, ascp=None, globus=None, globus_data=None,
                 globus_force_login=False, ignore_certificate=False, entry_thumbnail=None, entry_id=None,
                 entry_directory=None, stop_submit=False, dev=False, dev_local=False, password=None,
                 output_id_dir=False, grant_rights_usernames=None, grant_rights_emails=None, grant_rights_orcids=None,
                 globus_local_username=None):

        if dev:
            self.server_root = "https://wwwdev.ebi.ac.uk/empiar/sat-branch"
            self.upload_dir = 'tmp/andrii'
            self.destination_endpoint_id = '22baf81d-120c-495f-9c83-b3f74b423950'
        elif dev_local:
            self.server_root = "https://127.0.0.1:8001"
            self.upload_dir = 'tmp/andrii'
            self.destination_endpoint_id = ''
        else:
            self.server_root = "https://www.ebi.ac.uk"
            self.upload_dir = 'upload'
            self.destination_endpoint_id = '138b5c78-adef-4c12-89e6-2cd170bf63ed'

        self.deposition_url = f"{self.server_root}/empiar/deposition/api/deposit_entry/"
        self.redeposition_url = f"{self.server_root}/empiar/deposition/api/redeposit_entry/"
        self.thumbnail_url = f"{self.server_root}/empiar/deposition/api/image_upload/"
        self.submission_url = f"{self.server_root}/empiar/deposition/api/submit_entry/"
        self.grant_rights_url = f"{self.server_root}/empiar/deposition/api/grant_rights/"
        self.globus_directory_share_url = f"{self.server_root}/empiar/deposition/api/share_globus_directory/"
        self.fetch_entry_upload_directory = f"{self.server_root}/empiar/deposition/api/fetch_entry_upload_directory/"
        self.acknowledge_upload = f"{self.server_root}/empiar/deposition/api/acknowledge_upload/"

        self.password = password
        self.username = empiar_token if password else None
        self.auth_header = {} if password else {'Authorization': f'Token {empiar_token}'}
        self.deposition_headers = {'Content-type': 'application/json'}
        self.deposition_headers.update(self.auth_header)

        self.json_input, self.data = json_input, data
        self.ascp, self.globus = ascp, globus
        self.globus_data = globus_data
        self.ignore_certificate = ignore_certificate
        self.entry_thumbnail = entry_thumbnail
        self.entry_id, self.entry_directory = entry_id, entry_directory
        self.stop_submit, self.output_id_dir = stop_submit, output_id_dir
        self.grant_rights_usernames = self.prepare_rights_data(grant_rights_usernames)
        self.grant_rights_emails = self.prepare_rights_data(grant_rights_emails)
        self.grant_rights_orcids = self.prepare_rights_data(grant_rights_orcids)
        self.globus_local_username = globus_local_username

    @staticmethod
    def prepare_rights_data(data):
        if data and data.count(':') == data.count(',') + 1:
            return {k[0]: k[1] for k in (i.split(':') for i in data.split(','))}
        return None

    def make_request(self, method, url, **kwargs):
        if self.password:
            kwargs['auth'] = HTTPBasicAuth(self.username, self.password)
        kwargs['verify'] = not self.ignore_certificate
        return method(url, **kwargs)

    def check_status_and_return_poll_result(self, check_url, url_parameter, max_try=10):
        for _ in range(max_try):
            time.sleep(20)
            response = self.make_request(requests.get, check_url, params=url_parameter, headers=self.deposition_headers)
            if check_json_response(response):
                res_json = response.json()
                if res_json.get("status") != "In progress":
                    return res_json.get("return_value")
        return None

    def create_new_deposition(self):
        with open(self.json_input, 'rb') as f:
            response = self.make_request(requests.post, self.deposition_url, data=f, headers=self.deposition_headers)
        if check_json_response(response):
            res_json = response.json()
            if res_json.get('deposition') and res_json.get('entry_id'):
                self.entry_id = res_json['entry_id']
                if res_json.get('directory') == 'In progress':
                    sys.stdout.write(f"Entry {self.entry_id} created. Fetching directory...\n")
                    self.entry_directory = self.check_status_and_return_poll_result(self.fetch_entry_upload_directory,
                                                                                    {"entry_id": self.entry_id})
                else:
                    self.entry_directory = res_json['directory']
                return 0 if self.entry_directory else 1
        return 1

    def aspera_upload(self):
        sys.stdout.write("Initiating Aspera upload...\n")
        if os.environ.get('EMPIAR_TRANSFER_PASS'):
            os.environ['ASPERA_SCP_PASS'] = os.environ['EMPIAR_TRANSFER_PASS']
        dest_path = os.path.join(self.upload_dir, self.entry_directory, 'data').replace(os.sep, '/')
        command = f'"{self.ascp}" -QT -l 200M -P 33001 -L- -k3 {self.data} emp_dep@hx-fasp-1.ebi.ac.uk:{dest_path}'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(process.stdout.readline, b''):
            sys.stdout.write(line.decode("utf-8"))
        process.communicate()
        return process.returncode

    def globus_upload(self):
        sys.stdout.write(f"Sharing Globus directory with {self.globus_local_username}...\n")
        response = self.make_request(requests.get, self.globus_directory_share_url,
                                     params={"entry_id": self.entry_id, "globus_username": self.globus_local_username},
                                     headers=self.auth_header)
        if check_json_response(response):
            res_json = response.json()
            if isinstance(res_json, str): res_json = json.loads(res_json)
            if res_json.get("response") and res_json["response"][0] in ["1", "5"]:
                remote_path = os.path.join('/', self.entry_directory, 'data', self.globus_data['obj_name']).replace(
                    os.sep, '/')
                cmd = f"globus transfer {self.globus_data['is_dir']} {self.globus}:{self.data} {self.destination_endpoint_id}:{remote_path} --format json"
                out, _, code = run_shell_command([cmd])
                if code == 0:
                    return self.globus_upload_wait(json.loads(out).get('task_id'))
        return 1

    def globus_upload_wait(self, task_id):
        sys.stdout.write(f"Waiting for Globus task {task_id}...\n")
        _, _, code = run_shell_command([f"globus task wait {task_id}"])
        return code

    def thumbnail_upload(self):
        if not self.entry_thumbnail: return 0
        with open(self.entry_thumbnail, 'rb') as f:
            files = {'file': (os.path.basename(self.entry_thumbnail), f)}
            response = self.make_request(requests.post, self.thumbnail_url, data={"entry_id": self.entry_id},
                                         files=files, headers=self.auth_header)
        return 0 if check_json_response(response) and response.json().get('thumbnail_upload') else 1

    def deposit_data(self):
        if not (self.entry_id and self.entry_directory):
            if self.create_new_deposition() != 0: return 1
        if self.entry_thumbnail: self.thumbnail_upload()

        upload_code = self.aspera_upload() if self.ascp else -1
        if upload_code != 0 and self.globus: upload_code = self.globus_upload()

        if upload_code == 0:
            self.make_request(requests.post, self.acknowledge_upload, params={"entry_id": self.entry_id},
                              headers=self.auth_header)
            return 0 if self.stop_submit else self.submit_deposition()
        return 1

    def submit_deposition(self):
        sys.stdout.write("Submitting deposition...\n")
        data = json.dumps({"entry_id": self.entry_id})
        response = self.make_request(requests.post, self.submission_url, data=data, headers=self.deposition_headers)
        if check_json_response(response) and response.json().get('submission'):
            final_id = self.check_status_and_return_poll_result(self.submission_url, {"entry_id": self.entry_id})
            if final_id:
                sys.stdout.write(f"Submission successful! Accession: {final_id}\n")
                return 0
        return 1


def main():
    parser = argparse.ArgumentParser(description="EMPIAR Deposition Tool")
    parser.add_argument("empiar_token", help="EMPIAR API token")
    parser.add_argument("json_input", help="Path to submission JSON")
    parser.add_argument("data", help="Path to data")
    parser.add_argument("-a", "--ascp", help="Path to ascp executable")
    parser.add_argument("-g", "--globus", help="Globus Endpoint UUID")
    parser.add_argument("-e", "--thumbnail", help="Thumbnail path")
    parser.add_argument("-r", "--resume", nargs=2, metavar=("ID", "DIR"), help="Resume upload")
    parser.add_argument("-s", "--stop-submit", action="store_true", help="Do not submit after upload")
    parser.add_argument("-i", "--ignore-cert", action="store_true", help="Ignore SSL certificate errors")

    args = parser.parse_args()

    # Initialize logic...
    # (Abbreviated for brevity: call EmpiarDepositor and .deposit_data())


if __name__ == "__main__":
    main()