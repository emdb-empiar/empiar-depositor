#!/usr/local/bin/python2.7
# encoding: utf-8
"""
empiar_depositor.py

Deposit an entry to EMPIAR.

Copyright [2018] EMBL - European Bioinformatics Institute
Licensed under the Apache License, Version 2.0 (the
"License"); you may not use this file except in
compliance with the License. You may obtain a copy of
the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. See the License for the
specific language governing permissions and limitations
under the License.

Version history
1.6b32, 20240229, Sriram Somasundharam: Complete re-do of script to remove ascp uploads and introduce workflows
1.6b31, 20240229, Sriram Somasundharam: JSON schema updated
1.6b30, 20230816, Andrii Iudin: Added scale field to the example JSON
1.6b29, 20230811, Sriram Somasundharam: JSON schema updated
1.6b28, 20211208, Kiyo Tsunezumi: Fix of the error in $id
1.6b27, 20211208, Andrii Iudin: Switched Scipion workflow field to a generic workflow file
1.6b26, 20211208, Andrii Iudin: Fix of links in README.rst
1.6b25, 20211015, Andrii Iudin: Added an option to specify workflows, JSON schema updated to the latest draft
1.6b24, 20210729, Andrii Iudin: Switched to top url
1.6b23, 20210113, Andrii Iudin: It is now possible to get entry id and directory as an output on successful deposition
without submitting the entry
1.6b22, 20201217, Andrii Iudin: Updated documentation
1.6b21, 20201216, Andrii Iudin: Added support of rights granting and of EER, PNG and JPEG image set formats and 4 BIT
INTEGER voxel type
1.6b20, 20200429, Andrii Iudin: Schema update - now we accept references to IDR.
1.6b19, 20200302, Andrii Iudin: It is now possible to upload Big Data Viewer HDF5 files.
1.6b18, 20200220, Andrii Iudin: Moved Scipion workflow outside of image sets.
1.6b17, 20200218, Andrii Iudin: Added Scipion workflow to the schema and the example JSON.
1.6b16, 20200211, Andrii Iudin: Switched to a dedicated development server for external developers.
1.6b15, 20200207, Andrii Iudin: Consolidating Schema with EMPIAR deposition interface.
1.6b14, 20200206, Andrii Iudin: Setup.py adjusted to faciliate the additional files.
1.6b13, 20200206, Andrii Iudin: Schema and tests are now a part of the Python module.
1.6b12, 20200206, Andrii Iudin: Added optional output of the entry ID and the directory name.
1.6b11, 20200114, Andrii Iudin: Basic Authentication is allowed as an alternative to Token Authentication.
1.6b10, 20191125, Andrii Iudin: Added an option to upload the data without submission to facilitate streaming
measurements.
1.6b9, 20191112, Andrii Iudin: Documentation update.
1.6b8, 20181030, Andrii Iudin: Update of requirements due to security vulnerability of requests package.
1.6b7, 20180820, Andrii Iudin: Fix of Aspera env password setting, adjustments for Python 3.
1.6b6, 20180820, Andrii Iudin: Added Globus support.
1.6b5, 20180913, Andrii Iudin: Documentation typo fixes.
1.6b4, 20180913, Andrii Iudin: Added Python 3 support.
1.6b3, 20180531, Andrii Iudin: Updated documentation.
1.6b2, 20180531, Andrii Iudin: Fix of a typo.
1.6b1, 20180531, Andrii Iudin: Added an option to re-deposit data.
1.5b1, 20180328, Andrii Iudin: Added Aspera checks, re-arranged the order of upload to make sure that the entry has not
been submitted yet.
1.4b1, 20180305, Andrii Iudin: Now using argparse.
0.4, 20180305, Andrii Iudin: Code refactoring, allowed resuming entry uploads.
0.3, 20180215, Andrii Iudin: Adjusted printouts, implemented.
an option to upload thumbnails and to specify Aspera password.
0.2, 20180214, Andrii Iudin: The deposition is now done.
in three steps: create entry, upload data, submit.
0.1, 20180213, Andrii Iudin: Initial version.
"""

__author__ = 'Andrii Iudin, Sriram Somasundharam'
__email__ = 'sriram@ebi.ac.uk'
__date__ = '2018-02-13'

import copy
import json
import os.path
import time
import traceback
import requests
import subprocess
import sys
import argparse
from getpass import getpass
from requests.auth import HTTPBasicAuth
from requests.models import Response

# Validation utility
try:
    from jsonschema import validate, exceptions
except ImportError:
    jsonschema = None


def run_shell_command(command_list):
    """
    Executes a system command securely using a list of arguments to prevent shell injection.

    Args:
        command_list (list): The command and its arguments.
    Returns:
        tuple: (stdout, stderr, returncode)
    """
    try:
        process = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False
        )
        p_out, p_err = process.communicate()
        return p_out, p_err, process.returncode
    except FileNotFoundError:
        return b"", b"Command not found. Is globus-cli installed?", 127


def check_json_response(response):
    """
    Checks if the server response is a valid Response object with a JSON content-type.
    """
    is_response = isinstance(response, Response)
    result = is_response and \
             hasattr(response, 'headers') and \
             hasattr(response.headers, 'get') and \
             response.headers.get('content-type') == 'application/json'
    return result


def validate_empiar_json(json_path, schema_path):
    """
    Validates the deposition JSON metadata against the official EMPIAR schema.
    """
    if not os.path.exists(schema_path):
        print(f"Warning: Schema file '{schema_path}' not found. Skipping deep validation.\n")
        return True

    try:
        with open(schema_path, 'r') as s_file, open(json_path, 'r') as i_file:
            schema_data = json.load(s_file)
            input_data = json.load(i_file)

            validate(instance=input_data, schema=schema_data)

            print("JSON schema validation successful.\n")
            return True

    except exceptions.ValidationError as ve:
        print(f"\n[!] Metadata Validation Error in '{json_path}':\n")
        print(f"    - Field Path: {ve.json_path}\n")
        print(f"    - Reason: {ve.message}\n")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse JSON. Check syntax: {str(e)}\n")
        return False
    except Exception as e:
        print(f"Unexpected validation error: {str(e)}\n")
        return False


class EmpiarDepositor:
    """
    Manages interactions with the EMPIAR Deposition API, including entry creation,
    rights management, and submission.
    """

    def __init__(
            self,
            empiar_token,
            json_input,
            server_root,
            data,
            globus_source_endpoint,
            ignore_certificate,
            entry_thumbnail,
            entry_id=None,
            entry_directory=None,
            stop_submit=False,
            password=None,
            output_id_dir=False,
            grant_rights_usernames=None,
            grant_rights_emails=None,
            grant_rights_orcids=None,
            globus_local_username=None,
            dev=False
    ):

        self.server_root = server_root
        self.deposition_url = self.server_root + "/empiar/deposition/api/deposit_entry/"
        self.redeposit_url = self.server_root + "/empiar/deposition/api/redeposit_entry/"
        self.thumbnail_url = self.server_root + "/empiar/deposition/api/image_upload/"
        self.submission_url = self.server_root + "/empiar/deposition/api/submit_entry/"
        self.grant_rights_url = self.server_root + "/empiar/deposition/api/grant_rights/"
        self.globus_directory_share_url = self.server_root + "/empiar/deposition/api/share_globus_directory/"
        self.fetch_entry_upload_directory = self.server_root + "/empiar/deposition/api/fetch_entry_upload_directory/"
        self.acknowledge_upload = self.server_root + "/empiar/deposition/api/acknowledge_upload/"

        self.username = empiar_token if password else None
        self.password = password
        self.auth_header = {'Authorization': 'Token ' + empiar_token} if not password else {}
        self.deposition_headers = {'Content-type': 'application/json'}
        self.deposition_headers.update(self.auth_header)

        self.json_input = json_input
        self.data = data
        self.globus_source_endpoint = globus_source_endpoint
        self.ignore_certificate = ignore_certificate
        self.entry_thumbnail = entry_thumbnail
        self.entry_id = entry_id
        self.entry_directory = entry_directory
        self.stop_submit = stop_submit
        self.globus_local_username = globus_local_username

        self.rights_data = {
            'u': self.prepare_rights_data(grant_rights_usernames),
            'e': self.prepare_rights_data(grant_rights_emails),
            'o': self.prepare_rights_data(grant_rights_orcids)
        }
        self.empiar_accession = None

    @staticmethod
    def prepare_rights_data(data):
        """
        Formats user rights input into a dictionary for API submission.
        """
        if data and data.count(':') == data.count(',') + 1:
            return {k[0]: k[1] for k in tuple(i.split(':') for i in data.split(','))}
        return None

    def make_request(self, request_method, *args, **kwargs):
        """
        Executes an HTTP request with either Token or Basic authentication.
        """
        if self.password:
            return request_method(*args, auth=HTTPBasicAuth(self.username, self.password), **kwargs)
        return request_method(*args, **kwargs)

    def check_status_and_return_poll_result(self, check_url, url_parameter, max_try=10):
        """
        Polls a specific API endpoint until a task is no longer in progress.
        """
        try_count = 0
        while try_count < max_try:
            time.sleep(30)
            try_count += 1
            response = self.make_request(requests.get, check_url, params=url_parameter,
                                         headers=self.deposition_headers)
            if check_json_response(response):
                res_json = response.json()
                print(f"{res_json}")
                if res_json.get("status") != "In progress":
                    return res_json.get("return_value") or res_json.get("empiar_id")
        raise TimeoutError(f"Polling failed after {max_try} attempts for URL: {check_url}")

    def create_new_deposition(self):
        """
        Initiates a new EMPIAR deposition by uploading metadata and fetching the upload directory.
        """
        try:
            with open(self.json_input, 'rb') as f:
                response = self.make_request(requests.post, self.deposition_url, data=f,
                                             headers=self.deposition_headers)
            if check_json_response(response):
                res_json = response.json()
                if res_json.get('deposition') is True:
                    self.entry_id = res_json['entry_id']
                    self.entry_directory = res_json['directory']
                    if self.entry_directory == 'In progress':
                        self.entry_directory = self.check_status_and_return_poll_result(
                            self.fetch_entry_upload_directory,
                            {"entry_id": self.entry_id})

            if self.entry_directory:
                print(
                    f"Successfully create initial deposition with entry ID: {self.entry_id} and upload directory: {self.entry_directory}\n")
                return True
            else:
                return False
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            print(f"Error occurred while trying create initial deposition: {e}\n")
            return False

    def redeposit(self):
        """
        Updates an existing EMPIAR deposition with new metadata.
        """
        with open(self.json_input, 'rb') as f:
            data_dict = json.load(f)
        data_dict['entry_id'] = self.entry_id
        response = self.make_request(requests.put, self.redeposit_url, json=data_dict,
                                     headers=self.deposition_headers)
        if check_json_response(response) and response.json().get('deposition'):
            self.entry_directory = response.json().get('directory')
            return True
        return False

    def grant_rights(self):
        """
        Assigns access rights to specific EMPIAR users for the deposition.
        """
        success = True
        for key, val in self.rights_data.items():
            if val:
                payload = {key: val, "entry_id": self.entry_id}
                res = self.make_request(requests.post, self.grant_rights_url, json=payload,
                                        headers=self.deposition_headers)
                if not (check_json_response(res) and res.status_code == 200):
                    success = False
        return True if success else False

    def thumbnail_upload(self):
        """
        Upload the thumbnail image that will represent the entry on EMPIAR pages
        """
        print("Initiating the upload of the thumbnail image...\n")
        try:
            with open(self.entry_thumbnail, 'rb') as f:
                files = {'file': (self.entry_thumbnail, f)}
                thumbnail_response = self.make_request(
                    requests.post,
                    self.thumbnail_url,
                    data={"entry_id": self.entry_id},
                    files=files,
                    headers=self.auth_header,
                    verify=self.ignore_certificate
                )

            if check_json_response(thumbnail_response):
                thumbnail_response_json = thumbnail_response.json()

                if thumbnail_response_json.get('thumbnail_upload') is True:
                    print("Successfully uploaded the thumbnail for EMPIAR deposition.\n")
                    return True
                else:
                    print("The upload of the thumbnail for EMPIAR deposition was not successful. "
                          "Returned response: %s\nStatus code: %s\n" %
                          (str(thumbnail_response_json), thumbnail_response.status_code))
                    return False

            print("The upload of the thumbnail was not successful (Invalid JSON response).\n")
            return False
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            print(f"An error occurred during thumbnail upload: {e}\n")
            return False

    def share_upload_directory(self):
        """
        Requests EMPIAR to share the server's Globus directory with the user's identity.
        """
        try:
            is_globus_directory_shared = False
            print("Sharing the Globus upload directory with the user:" + self.globus_local_username
                  + "\n")
            share_directory_response = self.make_request(
                requests.get, self.globus_directory_share_url,
                params={"entry_id": self.entry_id, "globus_username": self.globus_local_username},
                headers=self.auth_header, verify=self.ignore_certificate)

            if check_json_response(share_directory_response):
                share_directory_response_json = json.loads(share_directory_response.json())
                if "response" in share_directory_response_json:
                    if (share_directory_response_json["response"][0] == "1" or
                            share_directory_response_json["response"][0] == "5"):
                        if share_directory_response_json["response"][0] == "5":
                            print(share_directory_response_json["response"][1] + "\n")
                        is_globus_directory_shared = True
            return True if is_globus_directory_shared else False
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            print(f"Error occurred while tryung to share globus directory: {e}\n")
            return False

    def acknowledge_completion(self):
        """
        Notifies EMPIAR that the data transfer is finished and ready for validation.
        """
        res = self.make_request(requests.post, self.acknowledge_upload, params={"entry_id": self.entry_id},
                                headers=self.auth_header)
        return True if check_json_response(res) and res.json().get("response_code") == 1 else False

    def submit_deposition(self):
        """
        Finalizes the deposition and submits it for curation.
        """
        res = self.make_request(requests.post, self.submission_url, json={"entry_id": str(self.entry_id)},
                                headers=self.deposition_headers)
        if check_json_response(res) and res.json().get('submission'):
            self.empiar_accession = self.check_status_and_return_poll_result(self.submission_url,
                                                                             {"entry_id": self.entry_id})
            return True if self.empiar_accession else False
        return False


class GlobusHelper:
    """
    Encapsulates all Globus CLI interactions and validations.
    """

    def __init__(self, endpoint_search_parameter, local_data_path, force_login=False):
        self.endpoint_search_parameter = endpoint_search_parameter
        self.local_data_path = local_data_path
        self.force_login = force_login
        self.user_identity = None
        self.endpoint_id = None
        self.dir_flag = "-r"
        self.obj_name = None
        self.helper_status = None

    def login_and_identify(self):
        """
        Authenticates the user via Globus CLI and retrieves their identity.
        """
        print("Logging in to Globus...\n")
        cmd = ['globus', 'login']
        if self.force_login:
            cmd.append('--force')

        out, err, code = run_shell_command(cmd)

        success_login = b'You have successfully logged in to the Globus CLI' in out or \
                        b'You are already logged in' in out

        if not success_login or code != 0:
            self.helper_status = "ERRORED 2 A"
            raise Exception("Globus login failed. Please ensure globus-cli is configured.")

        print("Successfully logged in\n")

        out_who, err_who, code_who = run_shell_command(["globus", "whoami"])
        if err_who or code_who != 0:
            self.helper_status = "ERRORED 2 B"
            raise Exception("Could not fetch Globus identity. Check your connection.")

        self.user_identity = out_who.decode('utf-8').strip()
        print(f"Successfully fetched depositors Globus Identity: {self.user_identity}\n")
        return True

    def check_local_endpoint_id(self):
        """
        Resolves the user-provided endpoint name or UUID to a valid Globus Endpoint ID.
        """
        print(f"Checking if {self.endpoint_search_parameter} exists in local endpoints...\n")
        cmd = [
            "globus", "endpoint", "search",
            self.user_identity,
            "--filter-scope", "my-endpoints",
            "--format", "json"
        ]
        out, err, code = run_shell_command(cmd)

        if code != 0:
            self.helper_status = "ERRORED 2 C"
            raise Exception(f"Endpoint search failed for {self.user_identity}. Error: {err}")

        endpoints = json.loads(out)
        for endpoint in endpoints.get('DATA', []):
            if endpoint.get('display_name') == self.endpoint_search_parameter or \
                    endpoint.get('id') == self.endpoint_search_parameter:
                self.endpoint_id = endpoint['id']
                break

        if not self.endpoint_id:
            self.helper_status = "ERRORED 2 C"
            raise Exception(f"Could not find local collection: {self.endpoint_search_parameter}")

        print(f"Validated local endpoint: {self.endpoint_id}\n")
        return True

    def validate_path_access(self, data_path):
        """
        Verifies that the data path is accessible on the selected Globus endpoint.
        """
        print(f"Checking access for {data_path} on endpoint {self.endpoint_id}\n")

        if os.path.isdir(data_path):
            self.dir_flag = '-r'
            clean_path = data_path.rstrip(os.path.sep)
            command_check = ["globus", "ls", f"{self.endpoint_id}:{clean_path}", "--format", "json"]
        elif os.path.isfile(data_path):
            self.dir_flag = ''
            dir_path = os.path.dirname(data_path)
            file_name = os.path.basename(data_path)
            command_check = ["globus", "ls", f"{self.endpoint_id}:{dir_path}", "--filter", f"={file_name}", "--format",
                             "json"]
        else:
            self.helper_status = "ERRORED 2 D"
            raise Exception(f"Path does not exist locally: {data_path}")

        out, err, code = run_shell_command(command_check)
        if code != 0:
            self.helper_status = "ERRORED 2 D"
            raise Exception(f"Path {data_path} is not accessible on Globus endpoint {self.endpoint_id}")

        print(f"Success: {data_path} is accessible.\n")
        self.obj_name = os.path.basename(data_path.rstrip(os.path.sep))
        return True

    def validate_globus_details(self):
        """
        Orchestrates the sequence of Globus login, endpoint identification, and path validation.
        """
        try:
            if self.login_and_identify() and self.check_local_endpoint_id() and self.validate_path_access(
                    self.local_data_path):
                return {'status': 'COMPLETED', 'error_message': None}
            else:
                return {'status': "ERRORED 2 E",
                        'error_message': "One of the Globus Validation failed. Please check the logs."}
        except Exception as e:
            if not self.helper_status:
                self.helper_status = "ERRORED 2"
            traceback.print_exc(file=sys.stderr)
            print(f"Error occurred while trying to validate globus details: {e}")
            return {'status': self.helper_status, 'error_message': str(e)}

    def globus_upload(self, destination_directory, destination_endpoint_id):
        """
        Initializes the data transfer task to the EMPIAR destination.
        """
        print("Initiating the Globus transfer...\n")
        dest_path = os.path.join('/', destination_directory, 'data', self.obj_name)

        command_tr_init = [
            "globus", "transfer",
            "--label", "EMPIAR_Transfer_Task",
            "--format", "json"
        ]

        if self.dir_flag == "-r":
            command_tr_init.append("-r")

        command_tr_init.append(f"{self.endpoint_id}:{self.local_data_path}")
        command_tr_init.append(f"{destination_endpoint_id}:{dest_path}")

        out_tr_init, err_tr_init, retcode_tr_init = run_shell_command(command_tr_init)
        if retcode_tr_init != 0 or not out_tr_init:
            print(
                "Globus transfer initiation was not successful. Return code: %s.\nOutput:%s\nError message: %s\n" %
                (retcode_tr_init, out_tr_init, err_tr_init))
            return {'status': 'ERRORED 4 A', 'error_code': 'Globus transfer initiation was not successful'}

        try:
            tr_init_json = json.loads(out_tr_init)
        except ValueError:
            print("Error while processing transfer initiation result - the string does not contain a valid "
                  "JSON. Return code: %s.\nOutput:%s\nError message: %s\n" %
                  (retcode_tr_init, out_tr_init, err_tr_init))
            return {'status': 'ERRORED 4 A',
                    'error_message': 'Globus JSON transfer initiation result does not have a valid readable JSON structure'}

        if 'task_id' not in tr_init_json or not tr_init_json['task_id']:
            print("Error in locating Globus Transfer Task ID from the transfer initiation result. "
                  "Return code: %s.\nOutput:%s\nError message: %s\n" %
                  (retcode_tr_init, out_tr_init, err_tr_init))
            return {'status': 'ERRORED 4 B',
                    'error_message': 'Error in locating Globus Transfer Task ID from the transfer initiation result.'}
        else:
            task_id = tr_init_json['task_id']

        return self.globus_upload_wait(task_id)

    def globus_upload_wait(self, task_id):
        """
        Monitors a Globus transfer task until completion, with a 3-day timeout.
        """
        timeout = 259200
        print(f"Transfer in progress. Monitoring Task ID: {task_id}")
        print(f"The script will wait up to 3 days for completion...")

        command_tr_wait = [
            "globus", "task", "wait",
            task_id,
            "--timeout", str(timeout),
            "--heartbeat"
        ]

        out_tr_wait, err_tr_wait, retcode_tr_wait = run_shell_command(command_tr_wait)

        if retcode_tr_wait != 0:
            error_detail = err_tr_wait.decode('utf-8') if err_tr_wait else "Timeout or manual interruption"
            print(f"Transfer monitoring stopped. Status Code: {retcode_tr_wait}\nError: {error_detail}")
            return {
                'status': "ERRORED 4 C",
                'error_message': f'Globus transfer failed to complete within the 3-day window or encountered an error.'
            }

        print(f"Globus Task {task_id} completed successfully.")
        return {'status': 'COMPLETED', 'error_message': None}


def main():
    """
    Orchestrates the EMPIAR deposition workflow including validation, handshake, and transfer.
    """
    version = "1.6b32"
    prog = "empiar-depositor"

    usage = """
    To deposit the data into EMPIAR please follow these steps:
    1) Create a JSON file according to the structure provided in the example (see https://empiar.org/deposition/json_submission). 
    2) Download and install globus-cli tool (pip install globus-cli).
    3)Install globus-cli:
        3.a. Please install globus-cli: pip install globus-cli
        3.b. At times users have more collection locally, so please find your active globus local collection. Once installed globus-cli try the below commands:
            3.b.1. globus login
            3.b.2. globus endpoint search --filter-scope my-endpoints
             (copy the ID of the collection that you actively use and this is local Globus endpoint ID)
    4)Run the script as:
       empiar-depositor [-h] [-g GLOBUS] [-f] [-e ENTRY_THUMBNAIL] [-r ENTRY_ID ENTRY_DIR] [-i] [-v] EMPIAR_TOKEN JSON_INPUT DATA

    Examples:
    for running on dev:
    empiar_depositor -g **globus_local_endpoint_id** empiar-dev-tester -p **** /Users/test/Desktop/Work/EMPIAR/empiar_depositor/working_example.json /Users/test/Desktop/Work/EMPIAR/Data/copy_1 -d
    for running on prod:
    empiar_depositor -g **globus_local_endpoint_id** empiar-dev-tester -p **** /Users/test/Desktop/Work/EMPIAR/empiar_depositor/working_example.json /Users/test/Desktop/Work/EMPIAR/Data/copy_1
                """

    possible_rights_help_text = "Rights can be 1 - Owner, 2 - View only, 3 - View and Edit, 4 - View, Edit and Submit. There can be only one deposition owner."

    parser = argparse.ArgumentParser(prog=prog, usage=usage, add_help=False,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-h", "--help", action="help", help="Show this help message and exit.")

    parser.add_argument("empiar_token", metavar="EMPIAR_TOKEN", help="EMPIAR API token.")
    parser.add_argument("json_input", metavar="JSON_INPUT",
                        help="The location of the JSON with EMPIAR deposition information.")
    parser.add_argument("data", metavar="DATA",
                        help="The location of the data that you would like to upload to EMPIAR. It should contain "
                             "directories that correspond to the image set directories specified in the JSON file.")

    parser.add_argument("-p", "--password", action="store", default=None, const=True, nargs="?",
                        help="EMPIAR user's password. If the argument is used without a value, the script will prompt for the password.")

    parser.add_argument("-g", "--globus", required=True,
                        help="Globus local endpoint UUID or display name from which data will be uploaded.")

    parser.add_argument("-f", "--globus-force-login", action="store_true",
                        help="Force Globus login even if a valid token is found in the local machine.")

    parser.add_argument("-e", "--entry-thumbnail", help="Thumbnail image path.")

    parser.add_argument("-gu", "--grant-rights-usernames",
                        help="Grant rights. Provide a comma separated list of usernames and rights in format <username>:<rights>. %s" % possible_rights_help_text)

    parser.add_argument("-ge", "--grant-rights-emails",
                        help="Grant rights. Provide a comma separated list of emails addresses and rights in format <email_address>:<rights>. %s" % possible_rights_help_text)

    parser.add_argument("-go", "--grant-rights-orcids",
                        help="Grant rights. Provide a comma separated list of ORCiDs and rights in format <orcid>:<rights>. %s" % possible_rights_help_text)

    parser.add_argument("-r", "--resume", nargs=2, metavar=("ID", "DIR"),
                        help="Resume the deposition and upload of an existing entry. Entry ID and the directory name "
                             "where data will be uploaded are required.")

    parser.add_argument("-s", "--stop-submit", action="store_true",
                        help="Stop the script before the submission step. If the argument is used, the script will "
                             "create a deposition and upload data but it will not submit it for annotation.")

    parser.add_argument("-i", "--ignore-certificate", action="store_false", default=True, dest="ignore_certificate",
                        help="Activate this flag to skip the verification of SSL certificate.")

    parser.add_argument("-v", "--version", action="version", version=version,
                        help="Show program's version number and exit.")

    parser.add_argument("-d", "--development", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("-dl", "--development-local", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("-o", "--output-id-dir", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()
    endpoint_id = None

    steps = [
        "1. Validate provided meta-data and related files",
        "2. Validate Globus identities and collection",
        "3. Initiate EMPIAR deposition",
        "4. Initiate EMPIAR Globus Upload",
        "5. Submit Entry"
    ]
    status = ["NOT RUN"] * 5
    error_msg = ""

    print("*" * 40 + "\n")
    print("Initiating EMPIAR deposition script:\n\n")
    print("Workflow of the script:\n")
    for s in steps:
        print(f" - {s}\n")
    print("*" * 40 + "\n")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(script_dir, 'empiar_deposition.schema.json')
    if args.development:
        server_root = "https://wwwdev.ebi.ac.uk"
        destination_endpoint_id = '22baf81d-120c-495f-9c83-b3f74b423950'
    else:
        server_root = "https://www.ebi.ac.uk"
        destination_endpoint_id = '138b5c78-adef-4c12-89e6-2cd170bf63ed'

    try:
        print(f"\nInitiating the Validation of meta-data and entry related file\n")
        if not os.path.isfile(args.json_input):
            status[0] = "ERRORED 1 A"
            raise Exception("Error code - 1 A. Todo - Check if the metadata json file exists")
        if not validate_empiar_json(args.json_input, schema_file):
            status[0] = "ERRORED 1 B"
            raise Exception(f"Error code - 1 B.Todo - Check the validation errors shown above and fix them")
        if args.entry_thumbnail and not os.path.isfile(args.entry_thumbnail):
            status[0] = "ERRORED 1 C"
            raise Exception("Error code 1 C.Todo - Check if the thumbnail file exists")
        print(f"Validation of meta-data and entry related file completed successfully\n")
        print("*" * 40 + "\n")
        status[0] = "COMPLETED"

        print(f"\nInitiating the Validation of Globus Identities, local collection and data\n")
        globus_helper = GlobusHelper(
            args.globus,
            args.data,
            args.globus_force_login
        )
        globus_validation_result = globus_helper.validate_globus_details()
        if globus_validation_result['error_message']:
            status[1] = globus_validation_result['status']
            raise Exception(globus_validation_result['error_message'])
        print(f"\nValidation of Globus Identities, local collection and data completed successfully\n")
        print("*" * 40 + "\n")
        status[1] = "COMPLETED"

        args_clean_pwd = copy.deepcopy(args)
        if args.password is not None:
            if args.password is True:
                args.password = getpass('Please enter your EMPIAR password to continue:\n')
            args_clean_pwd.password = '****'

        print("\nInitiating the deposition of the EMPIAR entry\n")
        print("\nYou are performing the deposition into EMPIAR with following args: %s\n" % args_clean_pwd)

        depositor = EmpiarDepositor(
            empiar_token=args.empiar_token,
            json_input=args.json_input,
            server_root=server_root,
            data=args.data,
            globus_source_endpoint=endpoint_id,
            ignore_certificate=args.ignore_certificate,
            entry_thumbnail=args.entry_thumbnail,
            entry_id=args.resume[0] if args.resume else None,
            entry_directory=args.resume[1] if args.resume else None,
            stop_submit=args.stop_submit,
            password=args.password,
            output_id_dir=args.output_id_dir,
            grant_rights_usernames=args.grant_rights_usernames,
            grant_rights_emails=args.grant_rights_emails,
            grant_rights_orcids=args.grant_rights_orcids,
            globus_local_username=globus_helper.user_identity,
            dev=args.development
        )
        dep_result = depositor.redeposit() if args.resume else depositor.create_new_deposition()
        if not dep_result:
            status[2] = "ERRORED 3 A"
            raise Exception("Error 3 A - Failed to initiate EMPIAR deposition")

        print("Initiating the thumbnail upload\n")
        if args.entry_thumbnail and not depositor.thumbnail_upload():
            status[2] = "ERRORED 3 B"
            raise Exception("Error 3 B - Failed to upload thumbnail")

        if args.grant_rights_usernames or args.grant_rights_emails or args.grant_rights_orcids:
            print("Creating depositor grant rights\n")
            if not depositor.grant_rights():
                status[2] = "ERRORED 3 D"
                raise Exception("Error 3 D - Failed to create grant rights")

        print("Sharing the Globus upload directory with the user for enabling transfer\n")
        if not depositor.share_upload_directory():
            status[2] = "ERRORED 3 E"
            raise Exception("Error 3 E - Globus Directory Share failed")

        print("\nInitial deposition of the EMPIAR entry has completed successfully\n")
        print("*" * 40 + "\n")
        status[2] = "COMPLETED"

        print("\nInitiating Globus upload\n")

        globus_upload_result = globus_helper.globus_upload(
            destination_directory=depositor.entry_directory,
            destination_endpoint_id=destination_endpoint_id
        )
        if globus_upload_result['error_message']:
            status[3] = globus_upload_result['status']
            raise Exception(globus_upload_result['error_message'])

        if not depositor.acknowledge_completion():
            status[3] = "ERRORED 4 D"
            raise Exception("Error 4 D - Acknowledgment of deposition completion failed")

        print("\nGlobus Upload and Acknowledgment Completed Successfully\n")
        print("*" * 40 + "\n")
        status[3] = "COMPLETED"

        print("\nChecking and initiating the submission of the EMPIAR entry\n")
        if args.stop_submit:
            print("\nSubmission of entry is not chosen so skipping this step\n")
            status[4] = "NOT CHOSEN"
        elif depositor.submit_deposition():
            print("\nSubmission of the EMPIAR entry is completed successfully\n")
            print("*" * 40 + "\n")
            status[4] = "COMPLETED"
        else:
            status[4] = "ERRORED 6 A"
            raise Exception("Error 6 A - Submission failed")

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        error_msg = str(e)
        print(error_msg)

    print("\nSummary:\n")
    for i, step in enumerate(steps):
        print(f"{step} - {status[i]}\n")

    if error_msg:
        print(f"\n{error_msg}")
    else:
        print("*" * 40 + "\n")
        print(
            f"\nEntry **{depositor.entry_id}** deposited with data uploaded to directory **{depositor.entry_directory}** and successfully submitted to entry **{depositor.empiar_accession}**\n\n")
        print("*" * 40 + "\n")


if __name__ == "__main__":
    main()
