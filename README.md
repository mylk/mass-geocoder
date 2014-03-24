Installation
========================

Clone project
------------------------

	git clone https://github.com/mylk/mass-geocoder.git


Permissions
------------------------

The script needs execute permissions:

	chmod +x massgeocode.py


Dependencies
------------------------

Python interpreter has to be installed (script has been developed and tested on python 2.7.3-0ubuntu7).

Module MySQLdb for MySQL integration and apgparse for argument parsing and argument dependencies have to be installed:

    # For Debian-based distros
    # installs the python package manager
    sudo apt-get install python-pip

    # For Debian-based distros
    # installs OS dependencies for the MySQL-python module:
    sudo apt-get install build-essential python-dev libmysqlclient-dev

    sudo pip install MySQL-python
    sudo pip install argparse
