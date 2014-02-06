#!/usr/bin/python
# -*- coding: utf8 -*-

from sys import exc_info
from urllib2 import urlopen
from urllib import quote_plus
from json import loads
from string import ascii_lowercase, ascii_uppercase, digits
from hashlib import sha1
from random import choice
from MySQLdb import connect
from os import access, R_OK
from datetime import datetime
from argparse import ArgumentParser, Action, RawTextHelpFormatter
import config # database configuration file

# used in argsparse
args = ()
# stores exluded columns and their values from geocoding, for later use
geo_excluded = {}

# just enum error levels
class errorLevels:
    ERROR = "Error"
    WARN = "Warning"

# custom argsparse action
class ArgsDeps(Action):
    def __call__(self, parser, args, values, option = None):
        args.method = values

        if args.method == "file" and not args.f:
            parser.error("You use the file method, so you have to set the -f option.")

def setup_args():
    global args

    help_descr = help()
    argparser = ArgumentParser(description=help_descr, formatter_class=RawTextHelpFormatter)
    argparser.add_argument("-f", help="The file that contains the addresses to be queried.", required=False)
    argparser.add_argument("-m", "--method", help="The media that the addresses will be retrieved.", required=True, action=ArgsDeps)
    argparser.add_argument("--force", help="Queries will be executed to the database.", action="store_true", default=False)
    argparser.add_argument("--dump", help="Queries will be dumped in the terminal session.", action="store_true", default=True)
    argparser.add_argument("--inserts", help="The type of statements that the application will produce.", action="store_true", default=True)
    argparser.add_argument("--updates", help="The type of statements that the application will produce.", action="store_true", default=False)

    args = argparser.parse_args()

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
    f.write("" + now + "\t" + level + "\t" + "\t" + errorDesc.encode("utf-8").replace(", ", "\t") + "\n")
    f.close()

    # exiting on "error" error level
    if level == errorLevels.ERROR:
        # just exiting with any other than 0, just to be catchable by the os/other scripts
        exit(1);

def encode_data(data):
    if type(data) is long:
        return str(data)
    elif type(data) is str:
        return data.encode("utf-8")
    else:
        return data

def is_geo_excluded(field):
    try:
        config.db["COLS_EXCL_GEO"].index(field)
        return True
    except:
        return False

def store_geo_excluded(key, value):
    global geo_excluded

    if not geo_excluded.has_key(key):
        geo_excluded[key] = []

    geo_excluded[key].append(value)

def get_empty(value):
    if value == None:
        return ""
    else:
        return value

def get_addresses():
    if args.method == "file":
        file = args.f
        address_results = []

        # check if file exists and access rights are ok
        if access(file, R_OK):
            file = open(args.f, "r")
            addressesfile = file.read()

            for address in addressesfile.splitlines():
                address_results.append(address.split(";"))

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
        con.close()


        for row in rows:
            _row = []
            colIndex = 0

            # fetch values from dynamic amount of query columns
            for col in config.db["COLUMNS"]:
                if is_geo_excluded(col) == False:
                    _row.append(encode_data(get_empty(row[colIndex])))
                else:
                    store_geo_excluded(col, row[colIndex])
                colIndex += 1

            results.append(_row)

    else:
        log("Invalid method.", errorLevels.ERROR);

    return results

def check_geo_in_range(lat, lng, address):
    try:
        if (float(lat) > 33.329890114795035 and float(lat) < 43.936911706744986 and
           float(lng) > 14.353004693984985 and float(lng) < 35.380836725234985) or \
           (float(lat) > 34.41128705078732 and float(lat) < 35.80429713948756 and
           float(lng) > 32.0522051284413 and float(lng) < 34.68068413234755):
            return True
        else:
            log("Latitude or longitude values [" + str(lat) + "," + str(lng) + "] are INVALID (out of range). {query = '" + address + "'}...", errorLevels.WARN)
            return False
    except:
        log(exc_info(), errorLevels.WARN)
        return False

def output(results):
    queries = []
    queryIndex = 0

    if args.inserts and not args.updates:
        for data in results:
            queries.append("INSERT INTO places (email, uniqueid, category_id, address, city, prefecture, area, postal_code, lat, lng, phone_number, created_at) VALUES ('" + \
                    data["email"] + "', '" + data["uniqueid"] + "', " + data["category_id"] + ", '" + data["address"] + "', '" + data["city"] + "', '" + \
                    data["prefecture"] + "', '" + data["area"] + "', '" + data["postal_code"] + "', '" + data["lat"] + "', '" + data["lng"] + "', '" + \
                    data["phone_number"] + "', '" + data["created_at"] + "');")
    elif args.updates:
        for data in results:
            queries.append("UPDATE places SET lat = '" + data["lat"] + "', lng = '" + data["lng"] + "', status = " + data["status"] + " WHERE id = '" + data["place_id"] + "';")
            queryIndex += 1

    if args.dump and not args.force:
        for query in queries:
            print query
    elif args.force:
        try:
            con = connect(host=config.db["HOST"], user=config.db["USERNAME"], passwd=config.db["PASSWORD"], db=config.db["DATABASE"], charset="utf8")
        except:
            log(exc_info(), errorLevels.ERROR)

        for query in queries:
            cur = con.cursor()
            cur.execute(query)
            cur.close()

        con.commit()
        con.close()

def geocode(addresses, retry = False):
    results = []
    placeIndex = 0

    for address in addresses:
        # retry removing the prefecture
        if retry == False:
            # matching geocode result list item with its id
            place_id = str(geo_excluded["id"][placeIndex])
            # increase the place index on every first query (not on retries)
            placeIndex += 1

            fulladdress = address[0] + " " + address[1] + " " + address[2] + " " + address[4]
            print (u"" + str(place_id)) + " " + fulladdress
        else:
            fulladdress = address[0] + " " + address[1] + " " + address[2] + u" Ν. " + address[3] + " " + address[4]

        # UGLY fix
        if args.method == "db":
            fulladdress = fulladdress.encode("utf-8")

        request = urlopen("http://maps.googleapis.com/maps/api/geocode/json?sensor=false&language=el&region=gr&address=" + quote_plus(fulladdress))
        response = loads(request.read())

        if response["status"] == "OK":
            street = ""
            streetNumber = ""
            city = ""
            area = ""
            prefecture = ""
            postalCode = ""
            lat = ""
            lng = ""

            locationType = response["results"][0]["geometry"]["location_type"]
            addressComponents = response["results"][0]["address_components"]

            for component in addressComponents:
                if len(component["types"]) > 0:
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

            if lat != "" and lng != "":
                # check if geocoded place falls between the greek and cypriot coordinates
                in_range = check_geo_in_range(lat, lng, address);

                if(in_range):
                    uniqueid = generate_SHA1(16)

                    results.append(dict(
                        place_id = place_id,
                        email = "",
                        uniqueid = uniqueid,
                        category_id = "1",
                        status = "1",
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
            # UGLY fix
            if args.method == "db":
                fulladdress = fulladdress.decode("utf-8")

            log(u"Error " + response["status"] + " for address: " + fulladdress, errorLevels.WARN)

            if response["status"] == "ZERO_RESULTS" and retry == False:
                # recursively retry geocoding for the same address (prefecture will be added)
                geocode([address], True)

    return results

def help():
    return """
    Mass geocoder

    This tool mass geocodes using the Google Maps API,
    and produces SQL insert statements.

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

    addresses = get_addresses()
    results = geocode(addresses)

    output(results)

main()
