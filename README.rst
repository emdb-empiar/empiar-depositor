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

1. Create a JSON file according to the `schema <empiar_depositor/empiar_deposition.schema.json>`_. An
`example <empiar_depositor/tests/deposition_json/working_example.json>`_ of such a file.

2. Download and install `ascp tool <http://downloads.asperasoft.com/connect2/>`_ and/or install globus-cli (supported
version 1.7.0) with

   .. code:: bash

     pip install globus-cli==1.7.0

   Globus can be used as a separate upload option or as a fallback if Aspera fails.

3. Set the environmental variable for EMPIAR transfer password to the one that EMPIAR team has provided you with. Please
note that this is not the API token from 1) and is a separate password from the one that you create when registering
EMPIAR user.

   - On Linux and Mac OS X execute

     .. code:: bash

       export EMPIAR_TRANSFER_PASS=<empiar_transfer_password>

   - On Windows execute

     .. code:: batch

       set EMPIAR_TRANSFER_PASS=<empiar_transfer_password>

4. Run the script as:

   .. code:: bash

     empiar-depositor [-h] [-a ASCP] [-g GLOBUS] [-f] [-e ENTRY_THUMBNAIL] [-r ENTRY_ID ENTRY_DIR] [-i] [-v] EMPIAR_TOKEN JSON_INPUT DATA

Positional arguments:
+++++++++++++++++++++

``EMPIAR_TOKEN``
~~~~~~~~~~~~~~~~
EMPIAR API token. You can generate it at
`https://empiar.org/deposition/api_token <https://empiar.org/deposition/api_token>`_. Alternatively, instead of the
token you can use your EMPIAR username and provide your password with **-p** optional argument (see below for more
information).

``JSON_INPUT``
~~~~~~~~~~~~~~
The location of the JSON with EMPIAR deposition information.

``DATA``
~~~~~~~~
The location of the data that you would like to upload to EMPIAR. It should contain directories that correspond to the
image set directories specified in the JSON file.

Optional arguments:
+++++++++++++++++++

``-h, --help``
~~~~~~~~~~~~~~
Show help message and exit

``-p PASSWORD, --password PASSWORD``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Use basic authentication (username + password) instead of token authentication. If no password is provided for this
argument, then the user is prompted for a password.

``-a ASCP, --ascp ASCP``
~~~~~~~~~~~~~~~~~~~~~~~~
The location of the ascp executable. By default it is installed in ~/.aspera/connect/bin directory on Linux machines,
in ~/Applications/Aspera\\ Connect.app/Contents/Resources directory on Macs and in
C:\\Users\\<username>\\AppData\\Local\\Programs\\Aspera\\Aspera Connect\\bin on Windows.

``-g GLOBUS, --globus GLOBUS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Use Globus if Aspera is not specified or Aspera transfer fails. Requirement: globus-cli installed and an endpoint
created. Specify your unique user identifier (UUID) as the input parameter.

``-f, --globus-force-login``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Force login to Globus. Login even if the globus-cli already has valid login credentials. Any existing credentials will
be removed from local storage and globally revoked.

``-e ENTRY_THUMBNAIL, --entry-thumbnail ENTRY_THUMBNAIL``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Thumbnail image that will represent your deposition on EMPIAR pages. Minimum size is 400 x 400, preferred format is png.
If none is provided, then the image from the related EMDB entry will be used.

``-r ENTRY_ID ENTRY_DIR, --resume ENTRY_ID ENTRY_DIR``
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

``-i, --ignore-certificate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Activate this flag to skip the verification of SSL certificate.

``-v, --version``
~~~~~~~~~~~~~~~~~
Show program's version number and exit

Examples:
+++++++++

.. code:: bash

  empiar-depositor -a ~/Applications/Aspera\ Connect.app/Contents/Resources/ascp 0123456789 ~/Documents/empiar_deposition_1.json ~/Downloads/micrographs

.. code:: bash

  empiar-depositor -a ~/Applications/Aspera\ Connect.app/Contents/Resources/ascp 0123456789 ~/Documents/empiar_deposition_1.json ~/Downloads/micrographs -gu johndoe:1,jamessmith:3

.. code:: bash

  empiar-depositor -a ~/Applications/Aspera\ Connect.app/Contents/Resources/ascp 0123456789 ~/Documents/empiar_deposition_1.json ~/Downloads/micrographs -gu johndoe:4,jamessmith:1 -ge jeremycarpenter@email.com:3 -go 0000-0000-0000-0001:2,0000-0000-1000-0002:4

.. code:: bash

  empiar-depositor -r 10 ABC123 -e ~/Downloads/dep_thumb.png 0123456789 -g 01234567-89a-bcde-fghi-jklmnopqrstu ~/Documents/empiar_deposition_1.json ~/Downloads/micrographs

.. code:: bash

  empiar-depositor -a ~/Applications/Aspera\ Connect.app/Contents/Resources/ascp my_empiar_user -p my_empiar_password ~/Documents/empiar_deposition_1.json ~/Downloads/micrographs