================
EMPIAR depositor
================

Command line tool for depositing data into `Electron Microscopy Public Image Archive
<https://empiar.org>`_.

How to use
----------

Please follow these steps:

1. Create a JSON file according to the structure provided in the `example <https://empiar.org/deposition/json_submission>`_.

2. Download and install `ascp tool <http://downloads.asperasoft.com/connect2/>`_.

3. Set the environmental variable for Aspera password to the one that EMPIAR team has provided you with. Please note that this is not the API token from 1) and is a separate password from the one that you create when registering EMPIAR user.

   - On Linux and Mac OS X execute

     .. code:: bash

       export ASPERA_SCP_PASS=<empiar_aspera_password>

   - On Windows execute

     .. code:: batch

       set ASPERA_SCP_PASS=<empiar_aspera_password>

4. Run the script as:

   .. code:: bash

     empiar-depositor [-h] [-e ENTRY_THUMBNAIL] [-r RESUME RESUME] [-i] [-v] EMPIAR_TOKEN JSON_INPUT ASCP_PATH DATA_PATH

Positional arguments:
+++++++++++++++++++++

``EMPIAR_TOKEN``
~~~~~~~~~~~~~~~~
EMPIAR API token. Contact EMPIAR team to obtain it.

``JSON_INPUT``
~~~~~~~~~~~~~~
The location of the JSON with EMPIAR deposition information.

``ASCP``
~~~~~~~~
The location of the ascp executable. By default it is installed in ~/.aspera/connect/bin directory on Linux machines, in ~/Applications/Aspera\ Connect.app/Contents/Resources directory on Macs and in C:\Users\<username>\AppData\Local\Programs\Aspera\Aspera Connect\bin on Windows.

``DATA``
~~~~~~~~
The location of the data that you would like to upload to EMPIAR. It should contain directories that correspond to the image set directories specified in the JSON file.

Optional arguments:
+++++++++++++++++++

``-h, --help``
~~~~~~~~~~~~~~
Show help message and exit

``-e ENTRY_THUMBNAIL, --entry-thumbnail ENTRY_THUMBNAIL``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Thumbnail image that will represent your deposition on EMPIAR pages. Minimum size is 400 x 400, preferred format is png. If none is provided, then the image from the related EMDB entry will be used.

``-r ENTRY_ID ENTRY_DIR, --resume ENTRY_ID ENTRY_DIR``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Resume Aspera upload or re-deposit an entry. The entry has to be successfully created as specifying EMPIAR entry ID and entry directory is required. All entry metadata will be replaced with the one provided in the JSON file. Aspera transfer will continue from where it stopped.

``-i, --ignore-certificate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Activate this flag to skip the verification of SSL certificate.

``-v, --version``
~~~~~~~~~~~~~~~~~
Show program's version number and exit

Examples:
+++++++++

.. code:: bash

  empiar-depositor 0123456789 ~/Documents/empiar_deposition_1.json ~/Applications/Aspera\ Connect.app/Contents/\ Resources/ascp ~/Downloads/micrographs

.. code:: bash

  empiar-depositor -r 10 ABC123 -e ~/Downloads/dep_thumb.png 0123456789 ~/Documents/empiar_deposition_1.json ~/\ Applications/Aspera\ Connect.app/Contents/Resources/ascp ~/Downloads/micrographs