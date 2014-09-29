About
========================

Mass-geocode is a Python2 application used to geocode addresses,
in order to enrich your data with geographical coordinates of places.
The result of the application will be SQL statements, either INSERTs or UPDATEs, depending on your needs.

For geocoding the Google Geocoding free API is used.
The usage of the free API is restricted by usage limits, which are described here:
https://developers.google.com/maps/documentation/geocoding/#Limits

If you reach the limits, you are going to see the relevant error messages.

As source of data (the addresses to be geocoded), you can either use a flat file or a MySQL database.
See the "Configuration" section below, to see how to configure the application to use your data.


Installation
========================

Clone project
------------------------

	git clone https://github.com/mylk/mass-geocoder.git


Permissions
------------------------

The script needs execute permissions:

	chmod +x massgeocode.py


Configuration
========================

Before executing, you have to make a profile file, that will give the application the appropriate info to use your data.

You can have multiple profiles, one for each application/database that you need to geolocate its data.
The profiles must be located in the profiles/ directory and you can use each profile
by mentioning its name while executing the application (see below the "Example of execution" section).

In the profile, you can set:
- the database credentials and connection info,
- the query to be used to retrieve the data from your database
- the database query templaces to be produced (INSERTs or UPDATEs)
- the locales of your data

You can find a sample profile file in the profiles/ directory.

The application assumes that, either on database and flat files, you have the following data columns:

    "address", "area", "city", "prefecture", "postal_code"

Example of flat file:

    51 Franklin Street;South Boston;Boston;Massachusetts;02110
    660 York Street;San Francisco;San Francisco;California;94110

An example of a database table structure can be found in _db/ directory.

Example of execution
========================

    ./massgeocode.py --method db --profile myapp --updates --force

Explanation:
* Retrieving not geocoded places from the database,
* using the myapp profile,
* formatting into update statements,
* executing the statements directly to the database.

For more help executing the application:

    ./massgeocode.py --help


Dependencies
========================

Python interpreter has to be installed (script has been developed and tested on python 2.7.3).

Module MySQLdb for MySQL integration and argparse for argument parsing and argument dependencies have to be installed:

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
