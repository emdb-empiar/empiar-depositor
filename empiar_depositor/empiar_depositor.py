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

__author__ = 'Andrii Iudin'
__email__ = 'andrii@ebi.ac.uk'
__date__ = '2018-02-13'

import copy
import json
import os.path
import requests
import subprocess
import sys
import argparse
from getpass import getpass
from requests.auth import HTTPBasicAuth
from requests.models import Response


def run_shell_command(command):
    """
    Run shell command
    :param command: the command that will be executed
    :return: process return code
    """
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p_out, p_err = process.communicate()
    return p_out, p_err, process.returncode


def check_json_response(response):
    """
    Check if the response has JSON content type
    :param response: Response object of requests Python module
    :return: True if response has JSON content type, False otherwise
    """
    is_response = isinstance(response, Response)
    result = is_response and \
             hasattr(response, 'headers') and \
             hasattr(response.headers, 'get') and \
             response.headers.get('content-type') == 'application/json'
    return result


class EmpiarDepositor:
    """
    The :class:`EmpiarDepositor <EmpiarDepositor>` object, which is used to create EMPIAR deposition, upload data and
    submit the deposition for annotation
    """

    def __init__(self, empiar_token, json_input, data, ascp=None, globus=None, globus_data=None,
                 globus_force_login=False, ignore_certificate=False, entry_thumbnail=None, entry_id=None,
                 entry_directory=None, stop_submit=False, dev=False, dev_local=False, password=None,
                 output_id_dir=False, grant_rights_usernames=None, grant_rights_emails=None, grant_rights_orcids=None):

        if dev:
            self.server_root = "https://wwwdev.ebi.ac.uk/pdbe/emdb/external_test/master"
            self.upload_dir = 'tmp/andrii'
        elif dev_local:
            self.server_root = "https://127.0.0.1:8000"
            self.upload_dir = 'tmp/andrii'
        else:
            self.server_root = "https://www.ebi.ac.uk"
            self.upload_dir = 'upload'

        self.deposition_url = self.server_root + "/empiar/deposition/api/deposit_entry/"
        self.redeposition_url = self.server_root + "/empiar/deposition/api/redeposit_entry/"
        self.thumbnail_url = self.server_root + "/empiar/deposition/api/image_upload/"
        self.submission_url = self.server_root + "/empiar/deposition/api/submit_entry/"
        self.grant_rights_url = self.server_root + "/empiar/deposition/api/grant_rights/"

        if password:
            self.username = empiar_token
            self.auth_header = {
                'WWW-Authenticate': 'Basic realm="api"',
            }
        else:
            self.auth_header = {
                'Authorization': 'Token ' + empiar_token,
            }

        self.deposition_headers = {
            'Content-type': 'application/json',
        }
        self.deposition_headers.update(self.auth_header)

        self.json_input = json_input
        self.data = data
        self.password = password
        self.ascp = ascp
        self.globus = globus
        self.globus_data = globus_data
        self.globus_force_login = globus_force_login
        self.ignore_certificate = ignore_certificate
        self.entry_thumbnail = entry_thumbnail
        self.entry_id = entry_id
        self.entry_directory = entry_directory
        self.stop_submit = stop_submit
        self.output_id_dir = output_id_dir
        self.grant_rights_usernames = self.prepare_rights_data(grant_rights_usernames)
        self.grant_rights_emails = self.prepare_rights_data(grant_rights_emails)
        self.grant_rights_orcids = self.prepare_rights_data(grant_rights_orcids)

    @staticmethod
    def globus_upload_wait(task_id):
        """
        Wait for the Globus upload to finish
        """
        sys.stdout.write("Transfer in progress, waiting on task %s to complete\n" % task_id)
        command_tr_wait = ['globus task wait -vvv --format json %s' % task_id]

        process = subprocess.Popen(command_tr_wait, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Poll process for new output until finished
        while True:
            next_line = process.stdout.readline()
            if next_line == b'' and process.poll() is not None:
                break

            sys.stdout.write(next_line)
            sys.stdout.flush()

        out_tr_wait, err_tr_wait = process.communicate()
        retcode_tr_wait = process.returncode

        if retcode_tr_wait != 0 or err_tr_wait:
            sys.stdout.write("Error while waiting for the transfer to finish. Return code: %s.\nOutput:%s\nError "
                             "message: %s\n" % (retcode_tr_wait, out_tr_wait, err_tr_wait))

        return retcode_tr_wait

    @staticmethod
    def prepare_rights_data(data):
        """
        Turn the comma separated list of user-specific fields and rights into a dictionary
        :param data: a string that contains a comma separated list of colon separated user-specific fields and rights,
        for example, 'usernam1:2,username2:1'
        :return: a dictionary with user-specific fields as keys and corresponding rights as values, for example,
        {'username1': 2, 'username2': 1}
        """
        if data:
            if data.count(':') == data.count(',') + 1:
                data_ready = {k[0]: k[1] for k in tuple(i.split(':') for i in data.split(','))}
                return data_ready
        return None

    def make_request(self, request_method, *args, **kwargs):
        """
        Make a request - either using Basic Authentication or Token
        :param request_method: the method of request, such as requests.get or requests.post
        :param args: additional arguments for the request
        :return: the response from the request
        """
        if self.password:
            response = request_method(*args, auth=HTTPBasicAuth(self.username, self.password), **kwargs)
        else:
            response = request_method(*args, **kwargs)
        return response

    def create_new_deposition(self):
        """
        Create a new EMPIAR deposition
        """
        deposition_response = self.make_request(requests.post, self.deposition_url, data=open(self.json_input, 'rb'),
                                                headers=self.deposition_headers, verify=self.ignore_certificate)

        if check_json_response(deposition_response):
            deposition_response_json = deposition_response.json()

            if 'deposition' in deposition_response_json and deposition_response_json['deposition'] is True and \
                    deposition_response_json['directory'] and deposition_response_json['entry_id']:
                if not isinstance(deposition_response_json['entry_id'], int):
                    sys.stdout.write("Error occurred while trying to create an EMPIAR deposition. Returned entry id is "
                                     "not an integer number\n")
                    return 1

                self.entry_id = deposition_response_json['entry_id']
                self.entry_directory = deposition_response_json['directory']
                sys.stdout.write("EMPIAR deposition was successfully created. Your entry ID is %s and unique data "
                                 "directory is %s\n" % (deposition_response_json['entry_id'],
                                                        deposition_response_json['directory']))

                return 0

            else:
                sys.stdout.write("The creation of an EMPIAR deposition was not successful. Returned response: %s\n"
                                 "Status code: %s\n" % (str(deposition_response_json), deposition_response.status_code))

        return 1

    def redeposit(self):
        """
        Re-deposit the data into EMPIAR. Updates an existing deposition
        """
        with open(self.json_input, 'rb') as f:
            data_dict = json.load(f)

        data_dict['entry_id'] = self.entry_id
        json_obj = json.dumps(data_dict, ensure_ascii=False).encode('utf8')
        redeposition_response = self.make_request(requests.put, self.redeposition_url, data=json_obj,
                                                  headers=self.deposition_headers, verify=self.ignore_certificate)

        if check_json_response(redeposition_response):
            redeposition_response_json = redeposition_response.json()

            if 'deposition' in redeposition_response_json and redeposition_response_json['deposition'] is True and \
                    redeposition_response_json['directory'] and redeposition_response_json['entry_id']:
                if not isinstance(redeposition_response_json['entry_id'], int):
                    sys.stdout.write("Error occurred while trying to update an EMPIAR deposition. Returned entry id is "
                                     "not an integer number\n")
                    return 1

                self.entry_id = redeposition_response_json['entry_id']
                self.entry_directory = redeposition_response_json['directory']
                sys.stdout.write("EMPIAR deposition was successfully updated. Your entry ID is %s and unique data "
                                 "directory is %s\n" % (redeposition_response_json['entry_id'],
                                                        redeposition_response_json['directory']))

                return 0

            else:
                sys.stdout.write("The update of an EMPIAR deposition was not successful. Returned response: %s\nStatus "
                                 "code: %s" % (str(redeposition_response_json), redeposition_response.status_code))

        sys.stdout.write("The update of the entry was not successful.\n")
        return 1

    def aspera_upload(self):
        """
        Upload the data via Aspera ascp command
        """
        sys.stdout.write("Initiating the Aspera upload...\n")

        transfer_pass = os.environ.get('EMPIAR_TRANSFER_PASS')
        if transfer_pass:
            os.environ['ASPERA_SCP_PASS'] = transfer_pass
        sys.stdout.write('data: ' + str(self.data) + '\n')
        sys.stdout.write('ED: ' + self.entry_directory + '\n')

        command = ['"' + self.ascp + '" -QT -l 200M -P 33001 -L- -k3 ' + self.data +
                   ' emp_dep@hx-fasp-1.ebi.ac.uk:' + os.path.join(self.upload_dir, self.entry_directory, 'data')]
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Poll process for new output until finished
        while True:
            next_line = process.stdout.readline()
            if next_line == b'' and process.poll() is not None:
                break

            sys.stdout.write(next_line.decode("utf-8"))
            sys.stdout.flush()

        process.communicate()

        return process.returncode

    def globus_upload(self):
        """
        Upload the data via globus-cli command
        """
        sys.stdout.write("Initiating the Globus upload...\n")

        # Initialise the data transfer
        command_tr_init = ["globus transfer --format json %s %s:%s d50a0618-6d04-11e5-ba46-22000b92c6ec:%s" %
                           (self.globus_data['is_dir'], self.globus, self.data,
                            os.path.join(self.upload_dir, self.entry_directory, 'data', self.globus_data['obj_name']))]

        out_tr_init, err_tr_init, retcode_tr_init = run_shell_command(command_tr_init)
        success_tr_init = b'The transfer has been accepted and a task has been created and queued for execution'
        if err_tr_init or retcode_tr_init != 0 or not out_tr_init or success_tr_init not in out_tr_init:
            sys.stdout.write(
                "Globus transfer initiation was not successful. Return code: %s.\nOutput:%s\nError message: %s\n" %
                (retcode_tr_init, out_tr_init, err_tr_init))
            return 1

        # Get task ID
        try:
            tr_init_json = json.loads(out_tr_init)
        except ValueError:
            sys.stdout.write("Error while processing transfer initiation result - the string does not contain a valid "
                             "JSON. Return code: %s.\nOutput:%s\nError message: %s\n" %
                             (retcode_tr_init, out_tr_init, err_tr_init))
            return 1

        if 'task_id' not in tr_init_json or not tr_init_json['task_id']:
            sys.stdout.write("Globus JSON transfer initiation result does not have a valid structure of "
                             "JSON['task_id']. Return code: %s.\nOutput:%s\nError message: %s\n" %
                             (retcode_tr_init, out_tr_init, err_tr_init))
            return 1
        else:
            task_id = tr_init_json['task_id']

        return self.globus_upload_wait(task_id)

    def thumbnail_upload(self):
        """
        Upload the thumbnail image that will represent the entry on EMPIAR pages
        """
        sys.stdout.write("Initiating the upload of the thumbnail image...\n")
        f = open(self.entry_thumbnail, 'rb')
        files = {'file': (self.entry_thumbnail, f)}
        thumbnail_response = self.make_request(requests.post, self.thumbnail_url, data={"entry_id": self.entry_id},
                                               files=files, headers=self.auth_header, verify=self.ignore_certificate)
        f.close()

        if check_json_response(thumbnail_response):
            thumbnail_response_json = thumbnail_response.json()

            if 'thumbnail_upload' in thumbnail_response_json and thumbnail_response_json['thumbnail_upload'] is True:
                sys.stdout.write("Successfully uploaded the thumbnail for EMPIAR deposition.\n")
                return 0
            else:
                sys.stdout.write("The upload of the thumbnail for EMPIAR deposition was not successful. Returned "
                                 "response: %s\nStatus code: %s\n" % (str(thumbnail_response_json),
                                                                      thumbnail_response.status_code))

        sys.stdout.write("The upload of the thumbnail was not successful.\n")
        return 1

    def grant_rights(self):
        """
        Grant rights to users
        """
        sys.stdout.write("Initiating the granting rights to the deposition...\n")
        if self.entry_id:
            data_list = []
            grant_rights_successes = {}
            if self.grant_rights_usernames:
                data_list.append({'u': self.grant_rights_usernames})
                for username in self.grant_rights_usernames:
                    grant_rights_successes[username] = False

            if self.grant_rights_emails:
                data_list.append({'e': self.grant_rights_emails})
                for email in self.grant_rights_emails:
                    grant_rights_successes[email] = False

            if self.grant_rights_orcids:
                data_list.append({'o': self.grant_rights_orcids})
                for orcid in self.grant_rights_orcids:
                    grant_rights_successes[orcid] = False

            for i in range(len(data_list)):
                data_dict = data_list[i]
                data_dict["entry_id"] = self.entry_id
                data_str = json.dumps(data_dict, ensure_ascii=False).encode('utf8')
                grant_rights_response = self.make_request(
                    requests.post, self.grant_rights_url, data=data_str,
                    headers=self.deposition_headers, verify=self.ignore_certificate
                )

                if check_json_response(grant_rights_response):
                    grant_rights_response_json = grant_rights_response.json()
                    for user_result in grant_rights_response_json:
                        if user_result and user_result in grant_rights_successes:
                            grant_rights_successes[user_result] = True

                    if grant_rights_response.status_code == 200:
                        sys.stdout.write(
                            "Successfully granted rights {data_dict} EMPIAR deposition {entry_id}.\n".format(
                                data_dict=data_dict,
                                entry_id=self.entry_id
                            )
                        )
                    else:
                        sys.stdout.write("The granting rights for EMPIAR deposition for %s was not successful. Returned "
                                         "response: %s\nStatus code: %s\n" % (data_dict,
                                                                              grant_rights_response_json,
                                                                              grant_rights_response.status_code))

            if not grant_rights_successes or False in grant_rights_successes.values():
                sys.stdout.write("The granting rights for EMPIAR deposition was not successful.")
                if grant_rights_successes:
                    sys.stdout.write(
                        "The following user(s) did not have rights granted: {grant_rights_successes}".format(
                            grant_rights_successes=grant_rights_successes
                        )
                    )
                return 1
        else:
            sys.stdout.write("Please provide an entry ID.")
            return 1

        return 0

    def submit_deposition(self):
        """
        Submit the deposition for annotation
        """
        sys.stdout.write("Initiating the submission of the deposition...\n")

        submission_response = self.make_request(requests.post, self.submission_url,
                                                data='{"entry_id": "%s"}' % self.entry_id,
                                                headers=self.deposition_headers, verify=self.ignore_certificate)

        if check_json_response(submission_response):
            submission_response_json = submission_response.json()
            if 'submission' in submission_response_json and submission_response_json['submission'] is True and \
                    submission_response_json['empiar_id']:
                sys.stdout.write("Your submission was successful. The accession code that can be cited in paper is %s\n"
                                 % submission_response_json['empiar_id'])
                if self.output_id_dir:
                    return self.entry_id, self.entry_directory
                return 0
            else:
                sys.stdout.write("The submission of an EMPIAR deposition was not successful. Returned response: %s\n"
                                 "Status code: %s\n" % (str(submission_response_json), submission_response.status_code))

        sys.stdout.write("The submission of the entry was not successful.\n")
        return 1

    def deposit_data(self):
        """
        Create, upload and submit a deposition to EMPIAR
        """
        upload_code = -1
        if not (self.entry_id and self.entry_directory):
            dep_code = self.create_new_deposition()
        else:
            dep_code = self.redeposit()

        if dep_code == 0:
            if self.entry_thumbnail:
                thumb_result = self.thumbnail_upload()
                if thumb_result != 0:
                    return thumb_result

            if self.ascp:
                upload_code = self.aspera_upload()
                if upload_code != 0 and self.globus:
                    sys.stdout.write("Error while uploading the data with Aspera. Trying to use Globus instead...\n")

            if upload_code != 0 and self.globus and self.globus_data:
                upload_code = self.globus_upload()

            if upload_code == 0:
                sys.stdout.write("Finished uploading the data.\n")

                grant_rights_exist = self.grant_rights_usernames or self.grant_rights_emails or self.grant_rights_orcids
                grant_rights_result = 0

                if grant_rights_exist:
                    grant_rights_result = self.grant_rights()

                if not grant_rights_exist or (grant_rights_exist and grant_rights_result == 0):
                    if self.stop_submit:
                        if self.output_id_dir:
                            return self.entry_id, self.entry_directory
                        return upload_code
                    else:
                        submit_result = self.submit_deposition()
                        return submit_result

        sys.stdout.write("The deposition of the entry was not successful.\n")
        return 1


def main(args=None):
    """
    Deposit the data into EMPIAR
    """
    try:
        # Handle command line args
        prog = "empiar-depositor"
        usage = """
    To deposit the data into EMPIAR please follow these steps:
    1) Create a JSON file according to the structure provided in the example (see https://empiar.org/\
deposition/json_submission).
    2) Download and install ascp tool (https://downloads.asperasoft.com/download_connect/) and/or install globus-cli 
tool (pip install globus-cli). Globus can be used as a separate upload option or as a fallback if Aspera fails.
    3) Set the environmental variable for EMPIAR transfer password to the one that EMPIAR team has provided you with. 
Please note that this is not the API token from 1) and is a password separate from the one that you create when 
registering an EMPIAR user.
        On Linux and Mac OS X execute
        export EMPIAR_TRANSFER_PASS=<empiar_transfer_password>

        On Windows execute
        set EMPIAR_TRANSFER_PASS=<empiar_transfer_password>
    4) Run the script as:
       empiar-depositor [-h] [-a ASCP] [-g GLOBUS] [-f] [-e ENTRY_THUMBNAIL] [-r ENTRY_ID ENTRY_DIR] [-i] [-v] \
EMPIAR_TOKEN JSON_INPUT DATA

    Examples:
    empiar-depositor -a ~/Applications/Aspera\ Connect.app/Contents/Resources/ascp 0123456789 ~/Documents/empiar_depo\
sition_1.json ~/Downloads/micrographs
    empiar-depositor -r 10 ABC123 -e ~/Downloads/dep_thumb.png 0123456789 -g 01234567-89a-bcde-fghi-jklmnopqrstu ~/Docu\
ments/empiar_deposition_1.json ~/Downloads/micrographs
                """
        version = "1.6b25"

        possible_rights_help_text = "Rights can be 1 - Owner, 2 - View only, 3 - View and Edit, 4 - View, Edit and " \
                                    "Submit. There can be only one deposition owner."
        parser = argparse.ArgumentParser(prog=prog, usage=usage, add_help=False,
                                         formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("-h", "--help", action="help", help="Show this help message and exit.")
        parser.add_argument("empiar_token", metavar="EMPIAR_TOKEN", help="EMPIAR API token.")
        parser.add_argument("json_input", metavar="JSON_INPUT",
                            help="The location of the JSON with EMPIAR deposition information.")
        parser.add_argument("data", metavar="DATA",
                            help="The location of the data that you would like to upload to EMPIAR. It should contain "
                                 "directories that correspond to the image set directories specified in the JSON file.")
        parser.add_argument("-p", "-password", action="store", default=None, const=True, nargs="?", dest="password",
                            help="Use basic authentication (username + password) instead of token authentication. If "
                                 "no password is provided for this argument, then the user is prompted for a password.")
        parser.add_argument("-a", "-ascp", action="store", default=False, dest="ascp",
                            help="The location of the ascp executable. By default it is installed in "
                                 "~/.aspera/connect/bin directory on Linux machines, in "
                                 "~/Applications/Aspera\ Connect.app/Contents/Resources directory on Macs and in "
                                 "C:\\Users\<username>\AppData\Local\Programs\Aspera\Aspera Connect\\bin on Windows.")
        parser.add_argument("-g", "--globus", action="store", default=False, dest="globus",
                            help="Use Globus if Aspera is not specified or Aspera transfer fails. Requirement: "
                                 "globus-cli installed and an endpoint created. Specify your unique user identifier "
                                 "(UUID) as the input parameter.")
        parser.add_argument("-f", "--globus-force-login", action="store_true", default=False, dest="globus_force_login",
                            help="Force login to Globus. Login even if the globus-cli already has valid login "
                                 "credentials. Any existing credentials will be removed from local storage and globally"
                                 " revoked.")

        parser.add_argument("-e", "--entry-thumbnail", action="store",
                            help="Thumbnail image that will represent your deposition on EMPIAR pages. Minimum size is "
                                 "400 x 400, preferred format is png. If none is provided, then the image from the "
                                 "related EMDB entry will be used.")

        parser.add_argument("-gu", "--grant-rights-usernames", action="store",
                            help="Grant rights. Provide a comma separated list of usernames and rights in format "
                                 "<username>:<rights>. " + possible_rights_help_text)
        parser.add_argument("-ge", "--grant-rights-emails", action="store",
                            help="Grant rights. Provide a comma separated list of emails addresses and rights in "
                                 "format <email_address>:<rights>. " + possible_rights_help_text)
        parser.add_argument("-go", "--grant-rights-orcids", action="store",
                            help="Grant rights. Provide a comma separated list of ORCiDs and rights in format "
                                 "<orcid>:<rights>. " + possible_rights_help_text)

        parser.add_argument("-r", "--resume", action="store", metavar=("ENTRY_ID", "ENTRY_DIR"),
                            help="Resume Aspera upload. The entry has to be successfully created beforehand as "
                                 "specifying EMPIAR entry ID and entry directory is required. Aspera transfer will "
                                 "continue from where it stopped.", nargs=2)
        parser.add_argument("-s", "--stop-submit", action="store_true", default=False, dest="stop_submit",
                            help="Do not submit the entry once the upload has finished.")
        parser.add_argument("-i", "--ignore-certificate", action="store_false", default=True, dest="ignore_certificate",
                            help="Activate this flag to skip the verification of SSL certificate.")
        parser.add_argument("-v", "--version", action="version", version=version, help="Show program's version number "
                                                                                       "and exit.")
        parser.add_argument("-d", "--development", action="store_true", default=False, help=argparse.SUPPRESS)
        parser.add_argument("-dl", "--development-local", action="store_true", default=False, help=argparse.SUPPRESS)
        parser.add_argument("-o", "--output-id-dir", action="store_true", default=False, help=argparse.SUPPRESS)

        if args is None:
            args = sys.argv[1:]
        args = parser.parse_args(args)

        json_file_exists = os.path.isfile(args.json_input)
        if not json_file_exists:
            sys.stdout.write("The specified JSON file does not exist\n")
            return 1

        if not (args.ascp or args.globus):
            sys.stdout.write("Please select a tool for the data transfer - either Aspera or Globus\n")
            return 1

        aspera_okay = True
        if args.ascp:
            aspera_exists = os.path.isfile(args.ascp)
            if aspera_exists:
                ascp_specified = args.ascp.endswith("ascp") or args.ascp.endswith("ascp.exe")
                if ascp_specified:
                    process = subprocess.Popen('"' + args.ascp + '"', shell=True, stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT)
                    p_out, p_err = process.communicate()

                    if not p_out or p_err:
                        sys.stdout.write("Error while trying to check ascp. Returned output:\n" + str(p_out) + "\n" +
                                         str(p_err) + "\n")
                        aspera_okay = False

                    ascp_is_working = b'Usage: ascp' in p_out and process.returncode == 112
                    if not ascp_is_working:
                        sys.stdout.write("The specified ascp does not work. Returned output:\n" + str(p_out) + "\n")
                        aspera_okay = False
                else:
                    sys.stdout.write(
                        "Please specify the correct path to ascp executable. By default it is installed in "
                        "~/.aspera/connect/bin directory on Linux machines, in ~/Applications/Aspera\ Connect.app/"
                        "Contents/Resources directory on Macs and in C:\\Users\<username>\AppData\Local\Programs\Aspera"
                        "\Aspera Connect\\bin on Windows\n")
                    aspera_okay = False
            else:
                sys.stdout.write("The specified Aspera executable does not exist\n")
                aspera_okay = False

        if not aspera_okay:
            if args.globus:
                sys.stdout.write("Will try using Globus instead\n")
            else:
                return 1

        globus_data = {}
        endpoint_id = None
        if args.globus:
            # Log in to Globus
            sys.stdout.write("Logging in to Globus...\n")
            command_login_str = 'globus login'
            if args.globus_force_login:
                command_login_str += ' --force'
            command_login = [command_login_str]

            out_login, err_login, retcode_login = run_shell_command(command_login)
            success_login = b'You have successfully logged in to the Globus CLI' in out_login or \
                            b'You are already logged in' in out_login
            if not success_login or err_login or retcode_login != 0:
                sys.stdout.write(
                    "Error while logging in into Globus. Return code: %s.\nOutput:%s\nError message: %s\n" %
                    (retcode_login, out_login, err_login))
                return 1
            sys.stdout.write("Successfully logged in\n")

            # Search for the source endpoint to get its ID
            command_es = ['globus endpoint search %s --filter-scope my-endpoints --format json' % args.globus]
            out_es, err_es, retcode_es = run_shell_command(command_es)

            if err_es or retcode_es != 0:
                sys.stdout.write("Error while searching for an endpoint. Return code: %s.\nOutput:%s\nError message: "
                                 "%s\n" % (retcode_es, out_es, err_es))
                return 1

            try:
                es_json = json.loads(out_es)
            except ValueError:
                sys.stdout.write(
                    "Error while processing endpoint search result - the string does not contain a valid JSON."
                    " Return code: %s.\nOutput:%s\nError message: %s\n" %
                    (retcode_es, out_es, err_es))
                return 1

            # Process the results depending on whether Globus endpoint name or its ID has been provided
            if 'DATA' in es_json and es_json['DATA']:
                for endpoint in es_json['DATA']:
                    if 'id' in endpoint and 'display_name' in endpoint:
                        if endpoint['display_name'] == args.globus or args.globus == endpoint['id']:
                            endpoint_id = endpoint['id']

                    else:
                        sys.stdout.write(
                            "Globus JSON endpoint search result does not have a valid structure of JSON['DATA']['id']."
                            " Return code: %s.\nOutput:%s\nError message: %s\n" %
                            (retcode_es, out_es, err_es))
                        return 1
                if not endpoint_id:
                    sys.stdout.write(
                        "Globus endpoint could not be found. Return code: %s.\nOutput:%s\nError message: %s\n" %
                        (retcode_es, out_es, err_es))
                    return 1
            else:
                sys.stdout.write(
                    "Globus JSON endpoint search result does not have a valid structure of JSON['DATA']['id']."
                    " Return code: %s.\nOutput:%s\nError message: %s\n" %
                    (retcode_es, out_es, err_es))
                return 1

            # Activate the source endpoint
            command_activate = ['globus endpoint activate %s --format json' % endpoint_id]
            out_activate, err_activate, retcode_activate = run_shell_command(command_activate)
            success_activation = b'Endpoint is already activated' in out_activate or \
                                 b'Autoactivation succeeded' in out_activate
            if err_activate or retcode_activate != 0 or not success_activation:
                sys.stdout.write(
                    "Globus endpoint cannot be activated. Return code: %s.\nOutput:%s\nError message: %s\n" %
                    (retcode_activate, out_activate, err_activate))
                return 1

            # Check that the source endpoint contains the specified data and determine if the data is a file or a
            # directory
            args.data = args.data.rstrip(os.path.sep)
            globus_data['is_dir'] = '-r'
            dir_path, globus_data['obj_name'] = args.data.rsplit(os.path.sep, 1)
            command_ls = ['globus ls %s:%s --format json' % (endpoint_id, args.data)]
            out_ls, err_ls, retcode_ls = run_shell_command(command_ls)

            if retcode_ls == 1 and b'\'' + args.data + b'\' is not a directory' in out_ls:
                globus_data['is_dir'] = False
                if os.path.sep in args.data:
                    command_ls = ['globus ls %s:%s --filter =%s --format json' % (endpoint_id, dir_path,
                                                                                  globus_data['obj_name'])]
                else:
                    command_ls = ['globus ls %s: --filter =%s --format json' % (endpoint_id, args.data)]

                out_ls, err_ls, retcode_ls = run_shell_command(command_ls)

            if retcode_ls != 0 or err_ls or b'"DATA":' not in out_ls:
                sys.stdout.write("Error while checking the existence of the object that is to be uploaded. Make sure "
                                 "that the path to the upload corresponds to the directory sharing settings in Globus. "
                                 "Return code: %s.\nOutput:%s\nError message: %s\n" %
                                 (retcode_ls, out_ls, err_ls))
                return 1

            # Activate the destination endpoint
            myproxy_pass = ''
            transfer_pass = os.environ.get('EMPIAR_TRANSFER_PASS')
            if transfer_pass:
                myproxy_pass = '--myproxy-password %s' % transfer_pass

            command_activate = ['globus endpoint activate --format json --myproxy --myproxy-username emp_dep '
                                '%s %s' % (myproxy_pass, endpoint_id)]
            out_activate, err_activate, retcode_activate = run_shell_command(command_activate)
            success_activation = b'Endpoint is already activated' in out_activate or \
                                 b'Endpoint activated successfully' in out_activate
            if err_activate or retcode_activate != 0 or not success_activation:
                sys.stdout.write(
                    "Globus endpoint cannot be activated. Return code: %s.\nOutput:%s\nError message: %s\n" %
                    (retcode_activate, out_activate, err_activate))
                return 1

        if args.entry_thumbnail:
            thumbnail_exists = os.path.isfile(args.entry_thumbnail)
            if not thumbnail_exists:
                sys.stdout.write("The specified thumbnail file does not exist\n")
                return 1

        data_exists = os.path.isfile(args.data) or os.path.isdir(args.data)
        if not data_exists:
            sys.stdout.write("The specified location of the data does not exist\n")
            return 1

        entry_id = None
        entry_directory = None
        if args.resume:
            if len(args.resume) == 2:
                [entry_id, entry_directory] = args.resume
            else:
                sys.stdout.write("You have to specify both entry ID and entry directory to be able to resume the "
                                 "deposition")
                return 1

        args_clean_pwd = copy.deepcopy(args)
        if args.password is not None:
            if args.password is True:
                args.password = getpass('Please enter your EMPIAR password to continue:\n')
            args_clean_pwd.password = '****'

        sys.stdout.write("You are performing the deposition into EMPIAR with following args: %s\n" % args_clean_pwd)

        emp_dep = EmpiarDepositor(
            empiar_token=args.empiar_token,
            json_input=args.json_input,
            data=args.data,
            ascp=args.ascp,
            globus=endpoint_id,
            globus_data=globus_data,
            globus_force_login=args.globus_force_login,
            ignore_certificate=args.ignore_certificate,
            entry_thumbnail=args.entry_thumbnail,
            entry_id=entry_id,
            entry_directory=entry_directory,
            stop_submit=args.stop_submit,
            dev=args.development,
            dev_local=args.development_local,
            password=args.password,
            output_id_dir=args.output_id_dir,
            grant_rights_usernames=args.grant_rights_usernames,
            grant_rights_emails=args.grant_rights_emails,
            grant_rights_orcids=args.grant_rights_orcids
        )

        dep_result = emp_dep.deposit_data()
        return dep_result

    except requests.exceptions.RequestException as e:
        sys.stdout.write(str(e) + '\n')
        return 1


if __name__ == "__main__":
    sys.exit(main())
