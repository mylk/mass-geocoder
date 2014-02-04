#!/usr/bin/python
# -*- coding: utf8 -*-

from urllib2 import urlopen
from urllib import quote_plus
from json import loads
from string import ascii_lowercase, ascii_uppercase, digits
from hashlib import sha1
from random import choice
from sys import argv
from MySQLdb import connect
from os import access, R_OK
from datetime import datetime
from argparse import ArgumentParser, Action
import config # database configuration file

args = ()

# just enum error levels
class errorLevels:
	ERROR = "Error"
	WARN = "Warning"

# custom argsparse action
class ArgsDeps(Action):
    def __call__(self, parser, args, values, option = None):
        args.method = values
        print args
        if args.method == "file" and not args.f:
            parser.error("You use the file method, so you have to set the -f option.")

def generate_unique_str(length):
    unique = ""
    charRange = ascii_lowercase + ascii_uppercase + digits

    for x in range(length):
        unique += choice(charRange)

    return unique

def generate_SHA1(length):
    # feed with rand str by exec generateUniqueStr(len)
    return sha1(generate_unique_str(24)).hexdigest()[0:length]

def log(error, level):
    now =  datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # check if error object passed or just string
    if type(error) is tuple:
        errorDesc = str(exc_info()[0]) + ", " + str(exc_info()[1])
    else:
        errorDesc = error

    print errorDesc

    # append error to error log file
    f = open("error.log", "a")
    f.write(now + "\t" + level + "\t" + "\t" + errorDesc.replace(", ", "\t") + "\n")
    f.close()

    # exiting on "error" error level
    if level == errorLevels.ERROR:
        # just exiting with any other than 0, just to be catchable by the os/other scripts
        exit(1);

def decode_data(data):
    if type(data) is long:
        return str(data)
    elif type(data) is str:
        return data.encode("utf-8")
    else:
        return data

def is_excluded_geo(field):
    try:
        config.db["COLS_EXCL_GEO"].index(field)
        return True
    except:
        return False

def get_addresses(method):
    if args.method == "file":
        file = args.f

        # check if file exists and access rights are ok
        if access(file, R_OK):
            file = open(argv[2], "r")
            addresses = file.read()
            addressesSplit = addresses.splitlines()
            file.close()

            return addressesSplit
        else:
            log("File does not exist.", errorLevels.ERROR);

    elif args.method == "db":
        try:
            con = connect(host=config.db["HOST"], user=config.db["USERNAME"], passwd=config.db["PASSWORD"], db=config.db["DATABASE"], charset="utf8")
        except:
            log(exc_info(), errorLevels.ERROR)

        results = []
        cur = con.cursor()
        cur.execute(config.db["QUERY"])
        rows = cur.fetchall()
        cur.close()


        for row in rows:
            _row = []
            colIndex = 0

            # fetch values from dynamic amount of query columns
            for col in config.db["COLUMNS"]:
                if is_excluded_geo(col) == False:
                    _row.append(decode_data(row[colIndex]))
                colIndex += 1

            results.append(u" ".join(_row))

    else:
        log("Invalid method.", errorLevels.ERROR);

    return results

def output(results):
    if args.dump:
        for data in results:
            print "INSERT INTO places (email, uniqueid, category_id, address, city, prefecture, area, postal_code, lat, lng, phone_number, created_at) VALUES ('" + \
                    data["email"] + "', '" + data["uniqueid"] + "', " + data["category_id"] + ", '" + data["address"] + "', '" + data["city"] + "', '" + \
                    data["prefecture"] + "', '" + data["area"] + "', '" + data["postal_code"] + "', '" + data["lat"] + "', '" + data["lng"] + "', '" + \
                    data["phone_number"] + "', '" + data["created_at"] + "');"
    elif args.force:
        for data im results:
            # updates to database

def setup_args():
    global args

    help_descr = help()
    argparser = ArgumentParser(description=help_descr)
    argparser.add_argument("-f", help="The file that contains the addresses to be queried.", required=False)
    argparser.add_argument("-m", "--method", help="The media that the addresses will be retrieved.", required=True, action=ArgsDeps)
    argparser.add_argument("--force", help="The media that the addresses will be retrieved.", action="store_true")
    argparser.add_argument("--dump", help="The media that the addresses will be retrieved.", action="store_true", default=True)

    args = argparser.parse_args()

def help():
        return """
        Mass geocoder

        This tools mass geocodes using the Google Maps API,
        and produces SQL insert statements.

        Usage:
        massgeocode.py -m method [-f addresses_file] --force | --dump

        Method can be any of the options below:
        - db
            Database connection configuration will be retrieved
            from config.py, placed in the current directory.
        - file
            It's recommended that the file has the following structure:
            - One address per line
            - Each line has the following information:
                street streetNumber city postalCode prefecture
        """

def main():
    setup_args()

    method = argv[1]
    addresses = get_addresses(method)
    results = []

    for address in addresses:
        request = urlopen("http://maps.googleapis.com/maps/api/geocode/json?sensor=false&language=el&address=" + quote_plus(address.encode("utf-8")))
        response = loads(request.read())

        if response["status"] == "OK":
            street = ""
            streetNumber = ""
            city = ""
            area = ""
            prefecture = ""
            postalCode = ""

            locationType = response["results"][0]["geometry"]["location_type"]
            addressComponents = response["results"][0]["address_components"]

            for component in addressComponents:
                componentType = component["types"][0]

                if componentType == "street_number":
                    streetNumber = component["long_name"]
                elif componentType == "route":
                    street = component["long_name"]
                elif componentType == "administrative_area_level_3":
                    city = component["long_name"]
                elif componentType == "country":
                    country = component["long_name"]
                elif componentType == "postal_code":
                    postalCode = component["long_name"]
                elif componentType == "political":
                    municipal = component["long_name"]
                elif componentType == "administrative_area_level_2":
                    prefecture = component["long_name"]

            lat = str(response["results"][0]["geometry"]["location"]["lat"])
            lng = str(response["results"][0]["geometry"]["location"]["lng"])

            uniqueid = generate_SHA1(16)

            results.append(dict(
                email = "",
                uniqueid = uniqueid,
                category_id = "1",
                address = "TRIM('" + street + " " + streetNumber + "')",
                city = city,
                prefecture = prefecture,
                area = area,
                postal_code = postalCode,
                lat = lat,
                lng = lng,
                phone_number = "",
                created_at = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ))

        else:
            print "Error " + response["status"] + " for address: " + address

    output(results)
main()
