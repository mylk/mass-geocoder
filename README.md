Installation
========================

Clone project
------------------------

	git clone https://github.com/mylk/mass-geocoder.git


Permissions
------------------------

The script needs execute permissions:

	chmod +x massgeocode.py


Example of execution
------------------------

    ./massgeocode.py --method db --profile myapp --updates --force

Explanation:
* Retrieving not geocoded places from the database,
* using the myapp profile,
* formatting into update statements,
* executing the statements directly to the database.

For help issuing the command:

    ./massgeocode.py --help


Dependencies
------------------------

Python interpreter has to be installed (script has been developed and tested on python 2.7.3).

Module MySQLdb for MySQL integration and apgparse for argument parsing and argument dependencies have to be installed:

    # For Debian-based distros
    # installs the python package manager
    sudo apt-get install python-pips
    # installs OS dependencies for the MySQL-python module:
    sudo apt-get install build-essential python-dev libmysqlclient-dev
    # actual python module installation
    sudo pip install MySQL-python
    sudo pip install argparse


    # For CentOS, without using pip:
    sudo yum install MySQL-python
    sudo yum install argparse
