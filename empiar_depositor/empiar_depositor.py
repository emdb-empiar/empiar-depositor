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

import json
import os.path
import requests
import subprocess
import sys
import argparse
from requests.models import Response


class EmpiarDepositor:
    """The :class:`EmpiarDepositor <EmpiarDepositor>` object, which is used to create EMPIAR deposition, upload data
    and submit the deposition for annotation
    """

    deposition_url = "https://www.ebi.ac.uk/pdbe/emdb/empiar/deposition/api/deposit_entry/"
    redeposition_url = "https://www.ebi.ac.uk/pdbe/emdb/empiar/deposition/api/redeposit_entry/"
    thumbnail_url = "https://www.ebi.ac.uk/pdbe/emdb/empiar/deposition/api/image_upload/"
    submission_url = "https://www.ebi.ac.uk/pdbe/emdb/empiar/deposition/api/submit_entry/"

    def __init__(self, empiar_token, json_input, ascp, data, ignore_certificate=False, entry_thumbnail=None,
                 entry_id=None, entry_directory=None):
        self.auth_header = {
            'Authorization': 'Token ' + empiar_token,
        }
        self.deposition_headers = {
            'Content-Type': 'application/json',
        }
        self.deposition_headers.update(self.auth_header)

        self.json_input = json_input
        self.ascp = ascp
        self.entry_thumbnail = entry_thumbnail
        self.data = data
        self.ignore_certificate = ignore_certificate
        self.entry_id = entry_id
        self.entry_directory = entry_directory

    def create_new_deposition(self):
        """
        Create a new EMPIAR deposition
        """
        deposition_response = requests.post(self.deposition_url, data=open(self.json_input, 'rb'),
                                            headers=self.deposition_headers, verify=self.ignore_certificate)

        if isinstance(deposition_response, Response):
            deposition_response_json = deposition_response.json()

            if 'deposition' in deposition_response_json and deposition_response_json['deposition'] is True and \
                    deposition_response_json['directory'] and deposition_response_json['entry_id']:
                if not isinstance(deposition_response_json['entry_id'], int):
                    sys.exit("Error occurred while trying to create an EMPIAR deposition. Returned entry id is not an "
                             "integer number\n")

                self.entry_id = deposition_response_json['entry_id']
                self.entry_directory = deposition_response_json['directory']
                sys.stdout.write("EMPIAR deposition was successfully created. Your entry ID is %s and unique data "
                                 "directory is %s\n" % (deposition_response_json['entry_id'],
                                                        deposition_response_json['directory']))

                return 0

            else:
                sys.exit("The creation of an EMPIAR deposition was not successful. Returned response: %s\nStatus code: "
                         "%s" % (str(deposition_response_json), deposition_response.status_code))

        sys.stdout.write("The deposition of entry was not successful.\n")
        sys.exit(1)

    def redeposit(self):
        """
        Re-deposit the data into EMPIAR. Updates an existing deposition
        """
        with open(self.json_input, 'rb') as f:
            data_dict = json.load(f)

        data_dict['entry_id'] = self.entry_id
        json_obj = json.dumps(data_dict, ensure_ascii=False).encode('utf8')
        redeposition_response = requests.post(self.redeposition_url, data=json_obj,
                                              headers=self.deposition_headers, verify=self.ignore_certificate)

        if isinstance(redeposition_response, Response):
            redeposition_response_json = redeposition_response.json()

            if 'deposition' in redeposition_response_json and redeposition_response_json['deposition'] is True and \
                    redeposition_response_json['directory'] and redeposition_response_json['entry_id']:
                if not isinstance(redeposition_response_json['entry_id'], int):
                    sys.exit("Error occurred while trying to update an EMPIAR deposition. Returned entry id is not an "
                             "integer number\n")

                self.entry_id = redeposition_response_json['entry_id']
                self.entry_directory = redeposition_response_json['directory']
                sys.stdout.write("EMPIAR deposition was successfully updated. Your entry ID is %s and unique data "
                                 "directory is %s\n" % (redeposition_response_json['entry_id'],
                                                        redeposition_response_json['directory']))

                return 0

            else:
                sys.exit("The update of an EMPIAR deposition was not successful. Returned response: %s\nStatus code: "
                         "%s" % (str(redeposition_response_json), redeposition_response.status_code))

        sys.stdout.write("The update of entry was not successful.\n")
        sys.exit(1)

    def aspera_upload(self):
        """
        Upload the data via Aspera ascp command
        """
        sys.stdout.write("Initiating the Aspera upload...\n")
        command = ['"' + self.ascp + '" -QT -l 200M -P 33001 -L- -k3 ' + self.data +
                   ' emp_dep@hx-fasp-1.ebi.ac.uk:upload/' + self.entry_directory + '/data']
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Poll process for new output until finished
        while True:
            next_line = process.stdout.readline()
            if next_line == '' and process.poll() is not None:
                break

            sys.stdout.write(next_line)
            sys.stdout.flush()

        process.communicate()

        if process.returncode == 0:
            return 0

        sys.stdout.write("The upload of the data was not successful.\n")
        sys.exit(process.returncode)

    def thumbnail_upload(self):
        """
        Upload the thumbnail image that will represent the entry on EMPIAR pages
        """
        sys.stdout.write("Initiating the upload of the thumbnail image...\n")
        f = open(self.entry_thumbnail, 'rb')
        files = {'file': (self.entry_thumbnail, f)}
        thumbnail_response = requests.post(self.thumbnail_url, data={"entry_id": self.entry_id}, files=files,
                                           headers=self.auth_header, verify=self.ignore_certificate)
        f.close()

        if isinstance(thumbnail_response, Response):
            thumbnail_response_json = thumbnail_response.json()

            if 'thumbnail_upload' in thumbnail_response_json and thumbnail_response_json['thumbnail_upload'] is True:
                sys.stdout.write("Successfully uploaded the thumbnail for EMPIAR deposition.")
                return 0
            else:
                sys.exit("The upload of the thumbnail for EMPIAR deposition was not successful. Returned response: %s\n"
                         "Status code: %s" % (str(thumbnail_response_json), thumbnail_response.status_code))

        sys.stdout.write("The upload of the thumbnail was not successful.\n")
        sys.exit(1)

    def submit_deposition(self):
        """
        Submit the deposition for annotation
        """
        sys.stdout.write("Initiating the submission of the deposition...\n")

        submission_response = requests.post(self.submission_url, data='{"entry_id": "%s"}' % self.entry_id, 
                                            headers=self.deposition_headers, verify=self.ignore_certificate)

        if isinstance(submission_response, Response):
            submission_response_json = submission_response.json()
            if 'submission' in submission_response_json and submission_response_json['submission'] is True and \
                    submission_response_json['empiar_id']:
                sys.stdout.write("Your submission was successful. The accession code that can be cited in paper is %s\n"
                                 % submission_response_json['empiar_id'])
                return 0
            else:
                sys.exit("The submission of an EMPIAR deposition was not successful. Returned response: %s\nStatus code"
                         ": %s" % (str(submission_response_json), submission_response.status_code))

        sys.stdout.write("The submission of entry was not successful.\n")
        sys.exit(1)

    def deposit_data(self):
        """
        Create, upload and submit a deposition to EMPIAR
        """
        if not (self.entry_id and self.entry_directory):
            dep_code = self.create_new_deposition()
        else:
            dep_code = self.redeposit()

        if dep_code == 0:
            if self.entry_thumbnail:
                self.thumbnail_upload()

            exit_code = self.aspera_upload()
            if exit_code == 0:
                sys.stdout.write("Finished uploading the data.\n")

                return self.submit_deposition()

        sys.stdout.write("The deposition of entry was not successful.\n")
        sys.exit(1)


def main():
    """
    Deposit the data into EMPIAR
    """
    try:
        # Handle command line args
        prog = "empiar-depositor"
        usage = """
    To deposit the data into EMPIAR please follow these steps:
    1) Create a JSON file according to the structure provided in the example (see https://empiar.org/\
deposition/json_submission)
    2) Download and install ascp tool (https://downloads.asperasoft.com/download_connect/)
    3) Set the environmental variable for Aspera password to the one that EMPIAR team has provided you with. Please \
note that this is not the API token from 1) and is a separate password from the one that you create when registering \
EMPIAR user.
        On Linux and Mac OS X execute
        export ASPERA_SCP_PASS=<empiar_aspera_password>

        On Windows execute
        set ASPERA_SCP_PASS=<empiar_aspera_password>
    4) Run the script as:
       empiar-depositor [-h] [-e ENTRY_THUMBNAIL] [-r RESUME RESUME] [-i] [-v] EMPIAR_TOKEN JSON_INPUT ASCP DATA

    Examples:
    empiar-depositor 0123456789 ~/Documents/empiar_deposition_1.json ~/Applications/Aspera\ Connect.app/Contents/\
Resources/ascp ~/Downloads/micrographs
    empiar-depositor -r 10 ABC123 -e ~/Downloads/dep_thumb.png 0123456789 ~/Documents/empiar_deposition_1.json ~/\
Applications/Aspera\ Connect.app/Contents/Resources/ascp ~/Downloads/micrographs
                """
        version = "1.6b1"

        parser = argparse.ArgumentParser(prog=prog, usage=usage, add_help=False)
        parser.add_argument("-h", "--help", action="help", help="Show this help message and exit.")
        parser.add_argument("empiar_token", metavar="EMPIAR_TOKEN", help="EMPIAR API token.")
        parser.add_argument("json_input", metavar="JSON_INPUT",
                            help="The location of the JSON with EMPIAR deposition information.")
        parser.add_argument("ascp", metavar="ASCP", help="The location of the ascp executable.")
        parser.add_argument("data", metavar="DATA",
                            help="The location of the data that you would like to upload to EMPIAR. It should contain "
                                 "directories that correspond to the image set directories specified in the JSON file.")

        parser.add_argument("-e", "--entry-thumbnail", action="store",
                            help="Thumbnail image that will represent your deposition on EMPIAR pages. Minimum size is "
                                 "400 x 400, preferred format is png. If none is provided, then the image from the "
                                 "related EMDB entry will be used.")
        parser.add_argument("-r", "--resume", action="store", metavar=("ENTRY_ID", "ENTRY_DIR"),
                            help="Resume Aspera upload. The entry has to be successfully created as specifying EMPIAR "
                                 "entry ID and entry directory is required. Aspera transfer will continue from where it"
                                 " stopped.", nargs=2)
        parser.add_argument("-i", "--ignore-certificate", action="store_false", default=True, dest="ignore_certificate",
                            help="Activate this flag to skip the verification of SSL certificate.")
        parser.add_argument("-v", "--version", action="version", version=version, help="Show program's version number "
                                                                                       "and exit.")
        args = parser.parse_args()

        json_file_exists = os.path.isfile(args.json_input)
        if not json_file_exists:
            sys.exit("The specified JSON file does not exist\n")

        aspera_exists = os.path.isfile(args.ascp)
        if not aspera_exists:
            sys.exit("The specified Aspera executable does not exist\n")

        ascp_specified = args.ascp.endswith("ascp") or args.ascp.endswith("ascp.exe")
        if not ascp_specified:
            sys.exit("Please specify the correct path to ascp executable. By default it is installed in "
                     "~/.aspera/connect/bin directory on Linux machines, in ~/Applications/Aspera\ Connect.app/"
                     "Contents/Resources directory on Macs and in C:\Users\<username>\AppData\Local\Programs\Aspera"
                     "\Aspera Connect\\bin on Windows\n")

        process = subprocess.Popen('"' + args.ascp + '"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p_out, p_err = process.communicate()
        ascp_is_working = "Usage: ascp" in p_out and process.returncode == 112
        if not ascp_is_working:
            sys.exit("The specified ascp does not work. Returned output:\n" + str(p_out) + "\n")

        if args.entry_thumbnail:
            thumbnail_exists = os.path.isfile(args.entry_thumbnail)
            if not thumbnail_exists:
                sys.exit("The specified thumbnail file does not exist\n")

        data_exists = os.path.isfile(args.data) or os.path.isdir(args.data)
        if not data_exists:
            sys.exit("The specified location of the data does not exist\n")

        entry_id = None
        entry_directory = None
        if args.resume:
            if len(args.resume) == 2:
                [entry_id, entry_directory] = args.resume
            else:
                sys.exit("You have to specify both entry ID and entry directory to be able to resume the deposition")

        sys.stdout.write("You are performing the deposition into EMPIAR with following args: %s\n" % args)

        emp_dep = EmpiarDepositor(args.empiar_token, args.json_input, args.ascp, args.data,
                                  args.ignore_certificate, args.entry_thumbnail, entry_id, entry_directory)

        return emp_dep.deposit_data()

    except requests.exceptions.RequestException as e:
        sys.stdout.write(str(e)+'\n')
        sys.exit(1)


if __name__ == "__main__":
    main()
