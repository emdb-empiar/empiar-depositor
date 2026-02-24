================
EMPIAR depositor
================

.. image:: https://badge.fury.io/py/empiar-depositor.svg
    :target: https://badge.fury.io/py/empiar-depositor

.. image:: https://img.shields.io/pypi/pyversions/empiar-depositor
    :alt: PyPI - Python Version

.. image:: https://travis-ci.org/emdb-empiar/empiar-depositor.svg?branch=dev
    :target: https://travis-ci.org/emdb-empiar/empiar-depositor

.. image:: https://coveralls.io/repos/github/emdb-empiar/empiar-depositor/badge.svg?branch=dev
    :target: https://coveralls.io/github/emdb-empiar/empiar-depositor?branch=dev

Command line tool for depositing data into `Electron Microscopy Public Image Archive
<https://empiar.org>`_.

How to use
----------

Please follow these steps:

1. Create a JSON file according to the `schema <https://github.com/emdb-empiar/empiar-depositor/blob/master/empiar_depositor/empiar_deposition.schema.json>`_. An
`example <https://github.com/emdb-empiar/empiar-depositor/blob/master/empiar_depositor/tests/deposition_json/working_example.json>`_ of such a file.

2. Download and install globus-cli (supported
version 1.7.0) with
   .. code:: bash

     pip install globus-cli==1.7.0

3. Please follow the below to fetch your source Globus endpoint ID for initiating Globus transfer.
    3.a. Login to your globus-cli

     .. code:: bash

      globus login

    3.b. Search and find ID of your source endpoint

    .. code:: bash

      globus endpoint search --filter-scope my-endpoints

    This will list all the available endpoint and please copy the ID of your chosen endpoint



4. Run the script as:

   .. code:: bash

     empiar-depositor [-h] [--token EMPIAR_TOKEN] [--endpoint LOCAL GLOBUS ENDPOINT] [--data-path DATA] [---metadata METADATA_JSON] [--thumbnail THUMBNAIL] [--resume ENTRY_ID ENTRY_DIR] [-i] [-v]

Required arguments:
+++++++++++++++++++++

``TOKEN``
~~~~~~~~~~~~~~~~
EMPIAR API token. You can generate it at
`https://empiar.org/deposition/api_token <https://empiar.org/deposition/api_token>`_. Alternatively, instead of the
token you can use your EMPIAR username and provide your password with **-p** optional argument (see below for more
information).

``METADATA``
~~~~~~~~~~~~~~
The location of the JSON with EMPIAR deposition information.

``ENDPOINT``
~~~~~~~~~~~~~~
The ID of the local GLobus collection endpoint

``DATA-PATH``
~~~~~~~~
The location of the data that you would like to upload to EMPIAR. It should contain directories that correspond to the
image set directories specified in the JSON file.

``THUMBNAIL``
~~~~~~~~
Thumbnail image that will represent your deposition on EMPIAR pages. Minimum size is 400 x 400, preferred format is png.
If none is provided, then the image from the related EMDB entry will be used.

Optional arguments:
+++++++++++++++++++

``-h, --help``
~~~~~~~~~~~~~~
Show help message and exit

``-p PASSWORD, --password PASSWORD``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Use basic authentication (username + password) instead of token authentication. If no password is provided for this
argument, then the user is prompted for a password.


``--resume ENTRY_ID ENTRY_DIR``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Resume Aspera upload or re-deposit an entry. The entry has to be successfully created as specifying EMPIAR entry ID and
entry directory is required. All entry metadata will be replaced with the one provided in the JSON file. Aspera transfer will continue from where it stopped.

``-gu USERNAME_RIGHTS, --grant-rights-usernames USERNAME_RIGHTS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``-ge EMAIL_RIGHTS, --grant-rights-emails EMAIL_RIGHTS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``-gu ORCID_RIGHTS, --grant-rights-usernames ORCID_RIGHTS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Grant rights based on usernames, emails or ORCiDs. ``USERNAME_RIGHTS``, ``EMAIL_RIGHTS`` and ``ORCID_RIGHTS`` are
comma separated lists of usernames, emails, ORCiDs and rights in format `username:rights`, `email:rights` and
`orcid:rights`. Rights can be 1 - Owner, 2 - View only, 3 - View and Edit, 4 - View, Edit and Submit. There can be
only one deposition owner.

``--ignore-certificate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Activate this flag to skip the verification of SSL certificate.

``--version``
~~~~~~~~~~~~~~~~~
Show program's version number and exit

``--production``
~~~~~~~~~~~~~~~~~
Create deposition adn submission in the EMPIAR produciton system

``--v``
~~~~~~~~~~~~~~~~~
Increase verbosity of the output.

``--log_file``
~~~~~~~~~~~~~~~~~
The location of the file where error logs can be created

Examples:
+++++++++

.. code:: bash

  empiar-depositor --token ********8a9b544ca36c6792f9e539e****** --endpoint afrtgb55-a058-11f0-bcb2-0affcauhjyh7 --data-path /Users/test/Desktop/Work/CLEMData/Data --metadata /Users/test/Desktop/Work/meta_data.json --thumbnail  /Users/test/Desktop/Work/empiar_test_entry_img.gif -v --log-file /Users/test/Desktop/Work/emp_dep.log

.. code:: bash

  empiar-depositor --token ********8a9b544ca36c6792f9e539e****** --endpoint afrtgb55-a058-11f0-bcb2-0affcauhjyh7 --data-path /Users/test/Desktop/Work/CLEMData/Data --metadata /Users/test/Desktop/Work/meta_data.json --thumbnail  /Users/test/Desktop/Work/empiar_test_entry_img.gif -v --log-file /Users/test/Desktop/Work/emp_dep.log --production
