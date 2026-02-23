#!/usr/bin/env python3
# encoding: utf-8
"""
empiar_depositor.py: A CLI tool to deposit entries to EMPIAR via Globus and API.
Copyright [2018] EMBL - European Bioinformatics Institute
Licensed under the Apache License, Version 2.0.
"""

__author__ = 'Andrii Iudin, Sriram Somasundharam'
__email__ = 'sriram@ebi.ac.uk'
__date__ = '2018-02-13'

import copy
import json
import logging
import os.path
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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


@dataclass
class CliError(Exception):
    """A CLI error that carries a stable error code and workflow step."""
    code: str
    step: str
    message: str
    detail: Optional[str] = None

    def __str__(self) -> str:
        base = f"[{self.code}] ({self.step}) {self.message}"
        return f"{base}\n{self.detail}" if self.detail else base


def _ensure(condition: bool, *, code: str, step: str, message: str, detail: Optional[str] = None) -> None:
    """Helper to raise CliError if a condition is not met."""
    if not condition:
        raise CliError(code=code, step=step, message=message, detail=detail)


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
    if not isinstance(response, Response):
        return False

    content_type = response.headers.get("content-type", "")
    return content_type.lower().startswith("application/json")


def validate_empiar_json(json_path, schema_path, logger):
    """
    Validates the deposition JSON metadata against the official EMPIAR schema.
    """
    json_path = Path(json_path)
    schema_path = Path(schema_path)

    if not schema_path.exists():
        logger.warning("Schema file not found at %s. Skipping schema validation.", schema_path)
        return True

    try:
        with open(schema_path, 'r') as s_file, open(json_path, 'r') as i_file:
            schema_data = json.load(s_file)
            input_data = json.load(i_file)
            validate(instance=input_data, schema=schema_data)
            logger.info("JSON schema validation successful.\n")
            return True

    except exceptions.ValidationError as ve:
        logger.error(f"\n[!] Metadata Validation Error in '{json_path}':\n")
        logger.error(f"    - Field Path: {ve.json_path}\n")
        logger.error(f"    - Reason: {ve.message}\n")
        return False
    except json.JSONDecodeError:
        logger.exception("Could not parse JSON file '%s'. Check syntax.", json_path)
        return False
    except Exception:
        logger.exception("Unexpected validation error while validating '%s'.", json_path)
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
            grant_rights_usernames=None,
            grant_rights_emails=None,
            grant_rights_orcids=None,
            globus_local_username=None,
            log=None
    ):
        """Initializes the depositor with API endpoints and authentication details."""
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
        self.log = log

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
                if res_json.get("status") != "In progress":
                    return res_json.get("return_value") or res_json.get("empiar_id")
        raise TimeoutError(f"Polling failed after {max_try} attempts for URL: {check_url}")

    def create_new_deposition(self):
        """
        Initiates a new EMPIAR deposition by uploading metadata and fetching the upload directory.
        """
        step = "empiar.create_deposition"
        try:
            with open(self.json_input, 'rb') as f:
                response = self.make_request(requests.post, self.deposition_url, data=f,
                                             headers=self.deposition_headers)
            _ensure(response.ok, code="E_API_CREATE_HTTP", step=step,
                    message=f"Failed to create deposition: HTTP {response.status_code}", detail=response.text[:800])
            _ensure(check_json_response(response), code="E_API_CREATE_JSON", step=step,
                    message="Create deposition did not return JSON", detail=str(response.headers))
            res_json = response.json()
            if res_json.get('deposition') is True:
                self.entry_id = res_json['entry_id']
                self.entry_directory = res_json['directory']
                if self.entry_directory == 'In progress':
                    self.entry_directory = self.check_status_and_return_poll_result(
                        self.fetch_entry_upload_directory,
                        {"entry_id": self.entry_id})

            _ensure(self.entry_directory, code="E_API_FETCH_ENTRY_DIR", step=step,
                    message="Create deposition did not create a valid entry directory", detail=str(response.headers))
        except Exception as e:
            self.log.exception("Unexpected error occurred while depositing entry with metadata at: '%s'.",
                               self.json_input)
            raise CliError(code="E_API_CREATE", step=step,
                           message="Unexpected error occurred while creating deposition.",
                           detail=str(e)) from e

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
        step = "empiar.grant_rights"
        for key, val in self.rights_data.items():
            if val:
                payload = {key: val, "entry_id": self.entry_id}
                response = self.make_request(requests.post, self.grant_rights_url, json=payload,
                                             headers=self.deposition_headers)
                _ensure(response.ok, code="E_API_GRANTS_HTTP", step=step,
                        message=f"Failed to grant rights: HTTP {response.status_code}", detail=response.text[:800])

    def thumbnail_upload(self):
        """
        Uploads the thumbnail image that will represent the entry on EMPIAR pages.
        """
        step = "empiar.thumbnail"
        self.log.info("Initiating the upload of the thumbnail image...\n")
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
            _ensure(thumbnail_response.ok, code="E_API_THUMB_HTTP", step=step,
                    message=f"Failed to upload thumbnail: HTTP {thumbnail_response.status_code}",
                    detail=thumbnail_response.text[:800])
            _ensure(check_json_response(thumbnail_response), code="E_API_THUMB_JSON", step=step,
                    message="Thumbnail upload did not return JSON", detail=str(thumbnail_response.headers))
            _ensure(thumbnail_response.json().get('thumbnail_upload'), code="E_API_THUMB_UPLOAD", step=step,
                    message="Thumbnail upload flag not set in response", detail=str(thumbnail_response.headers))
            self.log.info("Successfully uploaded the thumbnail for EMPIAR deposition.\n")

        except Exception as e:
            self.log.exception("Unexpected error occurred while uploading the thumbnail")
            raise CliError(code="E_API_THUMBNAIL", step=step,
                           message="Unexpected error occurred while uploading thumbnail.",
                           detail=str(e)) from e

    def share_upload_directory(self):
        """
        Requests EMPIAR to share the server's Globus directory with the user's identity.
        """
        try:
            step = "empiar.share_upload_directory"
            is_globus_directory_shared = False
            self.log.info(f"Sharing the Globus upload directory with the user: {self.globus_local_username}\n")
            share_directory_response = self.make_request(
                requests.get, self.globus_directory_share_url,
                params={"entry_id": self.entry_id, "globus_username": self.globus_local_username},
                headers=self.auth_header, verify=self.ignore_certificate)
            _ensure(share_directory_response.ok, code="E_API_SHARE_HTTP", step=step,
                    message=f"Failed to share entry directory: HTTP {share_directory_response.status_code}",
                    detail=share_directory_response.text[:800])

            share_directory_response_json = json.loads(share_directory_response.json())
            if "response" in share_directory_response_json:
                if (share_directory_response_json["response"][0] == "1" or
                        share_directory_response_json["response"][0] == "5"):
                    if share_directory_response_json["response"][0] == "5":
                        print(share_directory_response_json["response"][1] + "\n")
                    is_globus_directory_shared = True
            _ensure(is_globus_directory_shared, code="E_API_SHARE", step=step,
                    message="Directory sharing failed on server side", detail=str(share_directory_response.headers))
        except Exception as e:
            self.log.exception(
                "Unexpected error occurred while trying to share the upload directory for globus upload.")
            raise CliError(code="E_API_SHARE", step=step,
                           message="Unexpected error occurred while sharing entry directory.",
                           detail=str(e)) from e

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
        step = "empiar.submit"
        try:
            response = self.make_request(requests.post, self.submission_url, json={"entry_id": str(self.entry_id)},
                                         headers=self.deposition_headers)
            _ensure(response.ok, code="E_API_SUBMIT_HTTP", step=step,
                    message=f"Failed to create submission: HTTP {response.status_code}", detail=response.text[:800])
            _ensure(check_json_response(response), code="E_API_SUBMIT_JSON", step=step,
                    message="Submit deposition did not return JSON", detail=str(response.headers))
            res_json = response.json()
            if res_json.get('submission'):
                self.empiar_accession = self.check_status_and_return_poll_result(self.submission_url,
                                                                                 {"entry_id": self.entry_id})
            _ensure(self.empiar_accession, code="E_API_FETCH_ENTRY_ACCESSION", step=step,
                    message="Submit deposition did not create a valid entry accession code",
                    detail=str(response.headers))
        except Exception as e:
            self.log.exception("Unexpected error occurred while submitting the entry.")
            raise CliError(code="E_API_SUBMIT", step=step,
                           message="Unexpected error occurred while submitting the entry.",
                           detail=str(e)) from e


class GlobusHelper:
    """
    Encapsulates all Globus CLI interactions and validations.
    """

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        """Initializes the GlobusHelper with logging and path tracking."""
        self.user_identity: Optional[str] = None
        self.endpoint_id: Optional[str] = None
        self.endpoint_path: Optional[str] = None
        self.obj_name: str = ""
        self.dir_flag: str = ""
        self.log = logger or logging.getLogger(__name__)

    def login_and_identify(self):
        """
        Authenticates the user via Globus CLI and retrieves their identity.
        """
        self.log.info("Logging in to Globus...\n")
        step = "globus.login"
        cmd = ['globus', 'login']
        out, err, code = run_shell_command(cmd)

        success_login = b'You have successfully logged in to the Globus CLI' in out or \
                        b'You are already logged in' in out

        if not success_login or code != 0:
            raise CliError(code="E_GLOBUS_LOGIN", step=step, message="Globus login failed",
                           detail=(out + b"\n" + err).decode("utf-8", "replace")[:800])

        self.log.info("Successfully logged in\n")

        out_who, err_who, code_who = run_shell_command(["globus", "whoami"])
        if err_who or code_who != 0:
            raise CliError(code="E_GLOBUS_WHOAMI", step="globus.whoami",
                           message="Failed to fetch Globus identity (globus whoami)",
                           detail=(out + b"\n" + err).decode("utf-8", "replace")[:800])

        self.user_identity = out_who.decode('utf-8').strip()
        _ensure(bool(self.user_identity), code="E_GLOBUS_WHOAMI_EMPTY", step="globus.whoami",
                message="Globus identity is empty")
        self.log.info(f"Successfully fetched depositors Globus Identity: {self.user_identity}\n")

    def check_local_endpoint_id(self, endpoint_search):
        """
        Resolves the user-provided endpoint name or UUID to a valid Globus Endpoint ID.
        """
        self.log.info(f"Checking if {endpoint_search} exists in local endpoints...\n")
        step = "globus.endpoint_search"
        cmd = [
            "globus", "endpoint", "search",
            self.user_identity,
            "--filter-scope", "my-endpoints",
            "--format", "json"
        ]
        out, err, code = run_shell_command(cmd)

        if code != 0:
            raise CliError(code="E_GLOBUS_ENDPOINT_SEARCH", step=step, message="Globus endpoint search failed",
                           detail=(out + b"\n" + err).decode("utf-8", "replace")[:800])

        txt = out.decode("utf-8", "replace")
        endpoint_uuid = None
        endpoints = json.loads(out)
        for endpoint in endpoints.get('DATA', []):
            if endpoint.get('display_name') == endpoint_search or \
                    endpoint.get('id') == endpoint_search:
                endpoint_uuid = endpoint['id']
                break

        _ensure(endpoint_uuid is not None, code="E_GLOBUS_ENDPOINT_NOT_FOUND", step=step,
                message="No matching endpoint found", detail=txt[:800])
        self.endpoint_id = endpoint_uuid
        self.log.info(f"Validated local endpoint: {self.endpoint_id}\n")

    def validate_path_access(self, endpoint_path):
        """
        Verifies that the data path is accessible on the selected Globus endpoint.
        """
        step = "globus.ls"
        self.log.info(f"Checking access for {endpoint_path} on endpoint {self.endpoint_id}\n")

        if os.path.isdir(endpoint_path):
            self.dir_flag = '-r'
            clean_path = endpoint_path.rstrip(os.path.sep)
            command_check = ["globus", "ls", f"{self.endpoint_id}:{clean_path}", "--format", "json"]
        elif os.path.isfile(endpoint_path):
            self.dir_flag = ''
            dir_path = os.path.dirname(endpoint_path)
            file_name = os.path.basename(endpoint_path)
            command_check = ["globus", "ls", f"{self.endpoint_id}:{dir_path}", "--filter", f"={file_name}", "--format",
                             "json"]
        else:
            raise CliError(code="E_GLOBUS_DATA_CHECK", step=step, message=f"Globus local data path does not exist.",
                           detail=endpoint_path)

        out, err, code = run_shell_command(command_check)
        if code != 0:
            raise CliError(code="E_GLOBUS_LS", step=step, message="Failed to access endpoint path",
                           detail=(out + b"\n" + err).decode("utf-8", "replace")[:800])

        self.log.info(f"Success: {endpoint_path} is accessible.\n")
        self.endpoint_path = endpoint_path
        self.obj_name = os.path.basename(endpoint_path.rstrip(os.path.sep))

    def validate_globus_details(self, endpoint_search: str, endpoint_path: str) -> None:
        """
        Orchestrates the sequence of Globus login, endpoint identification, and path validation.
        """
        self.login_and_identify()
        self.check_local_endpoint_id(endpoint_search)
        _ensure(self.endpoint_id is not None, code="E_GLOBUS_ENDPOINT_ID", step="globus.endpoint_id",
                message="endpoint_id not set after search")
        self.validate_path_access(endpoint_path)

    def globus_upload(self, destination_directory, destination_endpoint_id, entry_reference):
        """
        Initializes the data transfer task to the EMPIAR destination.
        """
        step = "globus.transfer"
        self.log.info("Initiating the Globus transfer...\n")
        dest_path = os.path.join('/', destination_directory, 'data', self.obj_name)
        task_label = f"EMPIAR Transfer Task {entry_reference}"

        command_tr_init = [
            "globus", "transfer",
            "--label", task_label,
            "--format", "json"
        ]

        if self.dir_flag == "-r":
            command_tr_init.append("-r")

        command_tr_init.append(f"{self.endpoint_id}:{self.endpoint_path}")
        command_tr_init.append(f"{destination_endpoint_id}:{dest_path}")

        out_tr_init, err_tr_init, retcode_tr_init = run_shell_command(command_tr_init)
        if retcode_tr_init != 0 or not out_tr_init:
            raise CliError(code="E_GLOBUS_TRANSFER", step=step, message="Globus transfer command failed",
                           detail=(out_tr_init + b"\n" + err_tr_init).decode("utf-8", "replace")[:1200])
        txt = out_tr_init.decode("utf-8", "replace")
        task_id = None
        tr_init_json = json.loads(out_tr_init)
        if 'task_id' in tr_init_json and tr_init_json['task_id']:
            task_id = tr_init_json['task_id']
        _ensure(bool(task_id), code="E_GLOBUS_TASK_ID", step=step, message="Could not parse Globus task id from output",
                detail=txt[:1200])
        self.log.info(f"Successfully fetched Globus transfer task ID: {task_id}")
        self.globus_upload_wait(task_id)

    def globus_upload_wait(self, task_id):
        """
        Monitors a Globus transfer task until completion, with a 3-day timeout.
        """
        step = "globus.task_wait"
        timeout = 259200
        self.log.info(f"Transfer in progress. Monitoring Task ID: {task_id}")
        self.log.info(f"The script will wait up to 3 days for completion...")

        command_tr_wait = [
            "globus", "task", "wait",
            task_id,
            "--timeout", str(timeout),
            "--heartbeat"
        ]

        out_tr_wait, err_tr_wait, retcode_tr_wait = run_shell_command(command_tr_wait)

        if retcode_tr_wait != 0:
            raise CliError(code="E_GLOBUS_TASK_SHOW", step=step, message="Failed to query Globus task status",
                           detail=(out_tr_wait + b"\n" + err_tr_wait).decode("utf-8", "replace")[:1200])

        self.log.info(f"Globus Task {task_id} completed successfully.")


def main():
    """
    Orchestrates the EMPIAR deposition workflow including validation, handshake, and transfer.
    """
    version = "1.6.32"
    prog = "empiar-depositor"

    usage = """
    To deposit the data into EMPIAR please follow these steps:
    1) Create a JSON file according to the structure provided in the official schema.
    2) Download and install globus-cli tool (pip install globus-cli).
    3) Run the script providing the token, metadata JSON, and path to data.
                """

    possible_rights_help_text = "Rights: 1-Owner, 2-View, 3-Edit, 4-Submit. Only one owner allowed."

    parser = argparse.ArgumentParser(prog=prog, usage=usage, add_help=False,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-h", "--help", action="help", help="Show this help message and exit.")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity.")

    parser.add_argument("--user", required=False, help="EMPIAR username")
    parser.add_argument("--password", required=False, help="EMPIAR password")
    parser.add_argument("--token", required=True, help="EMPIAR API token")

    parser.add_argument("--metadata", dest="json_path", required=True, help="Path to deposition JSON metadata.")
    parser.add_argument("--thumbnail", required=True, help="Path to thumbnail image.")

    parser.add_argument("--endpoint", required=True, help="Globus source endpoint Name or UUID.")
    parser.add_argument("--data-path", dest="data_path", required=True, help="Local path on source endpoint to upload.")
    parser.add_argument("--force-login", action="store_true", help="Force Globus re-login.")
    parser.add_argument("--production", action="store_true", help="Use EMPIAR production server.")
    parser.add_argument("--destination-endpoint-id", default=None, help="Override destination Globus endpoint.")

    parser.add_argument("-gu", "--grant-rights-usernames",
                        help="Grant rights to usernames. %s" % possible_rights_help_text)
    parser.add_argument("-ge", "--grant-rights-emails", help="Grant rights to emails. %s" % possible_rights_help_text)
    parser.add_argument("-go", "--grant-rights-orcids", help="Grant rights to ORCiDs. %s" % possible_rights_help_text)

    parser.add_argument("--resume", nargs=2, metavar=("ID", "DIR"),
                        help="Resume an existing deposition (ID and DIR required).")
    parser.add_argument("--stop-submit", action="store_true", default=False, help="Do not submit after upload.")
    parser.add_argument("--ignore-certificate", action="store_false", default=True, dest="ignore_certificate",
                        help="Skip SSL verification.")
    parser.add_argument("--version", action="version", version=version, help="Show version.")
    parser.add_argument("--request-timeout", type=int, default=200, help="HTTP timeout in seconds.")
    parser.add_argument("--log-file", default=None, help="Path to log file.")

    args = parser.parse_args()

    console_level = logging.WARNING
    if args.verbose == 1:
        console_level = logging.INFO
    elif args.verbose >= 2:
        console_level = logging.DEBUG

    log = logging.getLogger("empiar-depositor")
    log.setLevel(logging.DEBUG)
    log.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(console)

    if args.log_file:
        fileh = logging.FileHandler(args.log_file)
        fileh.setLevel(logging.DEBUG)
        fileh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        log.addHandler(fileh)

    log.propagate = False

    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(script_dir, 'empiar_deposition.schema.json')
    steps = [
        "1. Validate provided meta-data and related files",
        "2. Validate Globus identities and collection",
        "3. Initiate EMPIAR deposition",
        "4. Initiate EMPIAR Globus Upload",
        "5. Submit Entry"
    ]
    status = ["NOT RUN"] * 5
    current_step = 0
    error_msg = ""

    if args.production:
        server_root = "https://www.ebi.ac.uk"
        destination_endpoint_id = '138b5c78-adef-4c12-89e6-2cd170bf63ed'
    else:
        server_root = "https://wwwdev.ebi.ac.uk"
        destination_endpoint_id = '22baf81d-120c-495f-9c83-b3f74b423950'

    if not args.token:
        _ensure(
            bool(args.password),
            code="E_ARGS_PASSWORD",
            step="cli.args",
            message="--password is required unless --token is provided",
        )

    log.info("*" * 40 + "\n")
    log.info("Initiating EMPIAR deposition script:\n\n")
    log.info("Workflow of the script:\n")
    for s in steps:
        log.info(f" - {s}\n")
    log.info("*" * 40 + "\n")

    try:
        log.info(f"\nInitiating Validation of meta-data and entry related files\n")
        json_path = Path(args.json_path)
        _ensure(json_path.exists(), code="E_INPUT_JSON_PATH", step="cli.inputs",
                message=f"Metadata JSON file not found", detail=str(json_path))

        if args.thumbnail:
            thumbnail_path = Path(args.thumbnail)
            _ensure(thumbnail_path.exists(), code="E_INPUT_THUMB_PATH", step="cli.inputs",
                    message=f"Entry thumbnail file not found", detail=str(thumbnail_path))

        if not validate_empiar_json(json_path, schema_path, log):
            raise CliError(code="E_SCHEMA", step="cli.validation",
                           message="Metadata JSON does not validate against schema")

        log.info(f"Validation of meta-data completed successfully\n")
        log.info("*" * 40 + "\n")
        status[0] = "COMPLETED"

        log.info(f"\nInitiating Validation of Globus Identities and collection\n")
        current_step = 1
        globus_helper = GlobusHelper(logger=log)
        globus_helper.validate_globus_details(endpoint_search=args.endpoint, endpoint_path=args.data_path)
        log.info(f"\nValidation of Globus details completed successfully\n")
        log.info("*" * 40 + "\n")
        status[1] = "COMPLETED"

        args_clean_pwd = copy.deepcopy(args)
        if args.password is not None:
            if args.password is True:
                args.password = getpass('Please enter your EMPIAR password to continue:\n')
            args_clean_pwd.password = '****'

        log.info("\nInitiating the deposition of the EMPIAR entry\n")
        current_step = 2

        depositor = EmpiarDepositor(
            empiar_token=args.token,
            json_input=args.json_path,
            server_root=server_root,
            data=args.data_path,
            globus_source_endpoint=globus_helper.endpoint_id,
            ignore_certificate=args.ignore_certificate,
            entry_thumbnail=args.thumbnail,
            entry_id=args.resume[0] if args.resume else None,
            entry_directory=args.resume[1] if args.resume else None,
            stop_submit=args.stop_submit,
            password=args.password,
            grant_rights_usernames=args.grant_rights_usernames,
            grant_rights_emails=args.grant_rights_emails,
            grant_rights_orcids=args.grant_rights_orcids,
            globus_local_username=globus_helper.user_identity,
            log=log
        )

        if args.resume:
            depositor.redeposit()
        else:
            depositor.create_new_deposition()

        if args.thumbnail:
            depositor.thumbnail_upload()

        if args.grant_rights_usernames or args.grant_rights_emails or args.grant_rights_orcids:
            depositor.grant_rights()

        depositor.share_upload_directory()
        log.info("\nInitial deposition of the EMPIAR entry completed successfully\n")
        log.info("*" * 40 + "\n")
        status[2] = "COMPLETED"

        log.info("\nInitiating Globus upload\n")
        current_step = 3
        globus_helper.globus_upload(
            destination_directory=depositor.entry_directory,
            destination_endpoint_id=destination_endpoint_id,
            entry_reference=depositor.entry_id
        )
        log.info("\nGlobus Upload completed successfully\n")
        log.info("*" * 40 + "\n")
        status[3] = "COMPLETED"

        log.info("\nInitiating submission of the EMPIAR entry\n")
        if args.stop_submit:
            log.info("\nSubmission skipped as requested\n")
            status[4] = "NOT CHOSEN"
        else:
            current_step = 4
            depositor.submit_deposition()
            log.info("\nSubmission completed successfully\n")
            log.info("*" * 40 + "\n")
            status[4] = "COMPLETED"

    except Exception as e:
        log.exception("Unexpected error occurred during execution.")
        status[current_step] = "ERRORED"
        error_msg = str(e)

    log.info("\nSummary:\n")
    for i, step_text in enumerate(steps):
        log.info(f"{step_text} - {status[i]}\n")

    if not error_msg:
        log.info("*" * 40 + "\n")
        log.info(
            f"Entry **{depositor.entry_id}** deposited to **{depositor.entry_directory}** and submitted as **{depositor.empiar_accession}**\n")
        log.info("*" * 40 + "\n")

    if error_msg:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except CliError as e:
        logging.error(str(e))
        sys.exit(2)
    except KeyboardInterrupt:
        logging.error("[E_INTERRUPT] Interrupted by user.")
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)