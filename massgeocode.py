#!/usr/bin/python
# -*- coding: utf8 -*-

from sys import exc_info, path
from io import open
from urllib2 import urlopen
from urllib import quote_plus
from json import loads
from MySQLdb import connect
from os import access, R_OK
from argparse import ArgumentParser, Action, RawTextHelpFormatter
import config # geocoding configuration file
from utils import utils # custom utils module

utils = utils()
__version__ = "1.1"

# used in argsparse
args = ()
# stores exluded columns and their values from geocoding, for later use
geo_excluded = {}
# stores profile object
profile = {}

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

# custom argsparse action
class LoadProfile(Action):
    def __call__(self, parser, args, values, option = None):
        args.profile = values

        global profile
        # append profiles subdir to the path variable, so we can import the profile
        path.insert(0, "./profiles")
        # import a module with a dynamic name
        profile = __import__(args.profile)

class MassGeocode:
    def __init__(self):
        self.setup_args()

    def setup_args(self):
        global args

        help_descr = self.help()
        argparser = ArgumentParser(description=help_descr, formatter_class=RawTextHelpFormatter)
        argparser.add_argument("-p", "--profile", help="The application profile.", required=True, action=LoadProfile)
        argparser.add_argument("-f", help="The file that contains the addresses to be queried.", required=False)
        argparser.add_argument("-m", "--method", help="The media that the addresses will be retrieved.", required=True, action=ArgsDeps)
        argparser.add_argument("--force", help="Queries will be executed to the database.", action="store_true", default=False)
        argparser.add_argument("--dump", help="Queries will be dumped in the terminal session.", action="store_true", default=True)
        argparser.add_argument("--inserts", help="The type of statements that the application will produce.", action="store_true", default=True)
        argparser.add_argument("--updates", help="The type of statements that the application will produce.", action="store_true", default=False)

        args = argparser.parse_args()

    def is_geo_excluded(self, field):
        try:
            profile.db["COLS_EXCL_GEO"].index(field)
            return True
        except:
            return False

    def store_geo_excluded(self, key, value):
        global geo_excluded

        if not geo_excluded.has_key(key):
            geo_excluded[key] = []

        geo_excluded[key].append(value)

    def get_addresses(self):
        results = []
        queriesResults = []
        queriesResultsFinal = []

        if args.method == "file":
            file = args.f
            addresses = []

            # check if file exists and access rights are ok
            if access(file, R_OK):
                file = open(args.f, "r", encoding='utf-8')
                addressesfile = file.read()

                # break the row to columns
                for _row in addressesfile.splitlines():
                    addresses.append(_row.split(";"))

                file.close()
            else:
                utils.log("File does not exist.", errorLevels.ERROR);

        elif args.method == "db":
            try:
                con = connect(host=profile.db["HOST"], user=profile.db["USERNAME"], passwd=profile.db["PASSWORD"], db=profile.db["DATABASE"], charset="utf8")
            except:
                utils.log(exc_info(), errorLevels.ERROR)

            cur = con.cursor()

            for query in profile.db["QUERIES"]:
                cur.execute(query)
                queriesResults.append(cur.fetchall())

            cur.close()
            con.close()
        else:
            utils.log("Invalid method.", errorLevels.ERROR);

        queryIndex = 0
        for queryResults in queriesResults:
            columns = profile.db["COLUMNS"][queryIndex]
            queryIndex += 1

            for address in queryResults:
                _row = []
                colIndex = 0

                # fetch values from dynamic amount of query columns
                for col in columns:
                    if self.is_geo_excluded(col) == False:
                        _row.append(utils.encode_data(utils.get_empty(address[colIndex])))
                    else:
                        self.store_geo_excluded(col, address[colIndex])
                    colIndex += 1

                results.append(_row)

            queriesResultsFinal.append(results)
            results = []

        #print repr(queriesResultsFinal).decode('raw_unicode_escape')

        return queriesResultsFinal

    def check_geo_in_range(self, lat, lng, address):
        try:
            if (float(lat) > 33.329890114795035 and float(lat) < 43.936911706744986 and
               float(lng) > 14.353004693984985 and float(lng) < 35.380836725234985) or \
               (float(lat) > 34.41128705078732 and float(lat) < 35.80429713948756 and
               float(lng) > 32.0522051284413 and float(lng) < 34.68068413234755):
                return True
            else:
                utils.log("Latitude or longitude values [" + str(lat) + "," + str(lng) + "] are INVALID (out of range). {query = '" + address + "'}...", errorLevels.WARN)
                return False
        except:
            utils.log(exc_info(), errorLevels.WARN)
            return False

    def output(self, results):
        queries = []
        queryIndex = 0

        if args.inserts and not args.updates:
            for data in results:
                queries.append(profile.prepare_insert(data))
        elif args.updates:
            for data in results:
                queries.append(profile.prepare_update(data))
                queryIndex += 1

        if args.dump and not args.force:
            for query in queries:
                print query
        elif args.force:
            try:
                con = connect(host=profile.db["HOST"], user=profile.db["USERNAME"], passwd=profile.db["PASSWORD"], db=profile.db["DATABASE"], charset="utf8")
            except:
                utils.log(exc_info(), errorLevels.ERROR)

            for query in queries:
                cur = con.cursor()
                cur.execute(query)
                cur.close()

            con.commit()
            con.close()

    def geocode(self, addresses, retry = False):
        results = []
        rowIndex = 0
        addressIndex = 0
        nextQuery = 0

        # use the results of the first query
        for address in addresses[0]:
            # retry removing the prefecture
            if retry == False:
                # matching geocode result list item with its id
                row_id = str(geo_excluded[profile.db["ROW_IDENTIFIER"]][rowIndex])
                # increase the row index on every first query (not on retries)
                rowIndex += 1

                fulladdress = " ".join(address)
                #print (u"" + str(row_id)) + " " + fulladdress

                # the index of the support query (if geocoding fails for the previous)
                nextQuery = 0
            else:
                nextQuery = 1

                # use the results of any support query (if geocoding failed for the other query)
                # if next query does not exist, use the last query available
                if not addresses[nextQuery]:
                    nextQuery = addresses.length - 1

                fulladdress = " ".join(addresses[nextQuery][addressIndex])

            addressIndex += 1

            # UGLY fix
            fulladdress = fulladdress.encode("utf-8")

            try:
                request = urlopen(u"http://maps.googleapis.com/maps/api/geocode/json?sensor=false&language=" + config.geocode["LANGUAGE"] + u"&region=" + config.geocode["REGION"] + u"&address=" + quote_plus(fulladdress))
            except:
                utils.log(exc_info(), errorLevels.ERROR)

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
                    # check if geocoded row falls between the greek and cypriot coordinates
                    in_range = self.check_geo_in_range(lat, lng, address);

                    if(in_range):
                        uniqueid = utils.generate_SHA1(16)

                        results.append(dict(
                            row_id = row_id,
                            uniqueid = uniqueid,
                            address = "TRIM('" + street + " " + streetNumber + "')",
                            city = city,
                            prefecture = prefecture,
                            area = area,
                            postal_code = postalCode,
                            lat = lat,
                            lng = lng,
                            created_at = utils.right_now()
                        ))
            else:
                # UGLY fix
                fulladdress = fulladdress.decode("utf-8")

                utils.log("Error " + response["status"] + " for address: " + fulladdress, errorLevels.WARN)

                if response["status"] == "ZERO_RESULTS" and retry == False:
                    # recursively retry geocoding for the same address (prefecture will be added)
                    self.geocode([address], True)

        return results

    def help(self):
        return """
         -Mass geocoder

        This tool mass geocodes using the Google Maps API,
        and produces SQL statements.

        The input method can be any of the below:
        - db
            Database connection configuration will be retrieved
            from config.py, placed in the current directory.
        - file
            It's recommended that the file has the following structure:
            - One address per line,
            - Each line has the following information:
                id street streetNumber city postalCode prefecture
            - The fields above, have to be seperated by semicolumns ";".
        """

    def run(self):
        addresses = self.get_addresses()
        results = self.geocode(addresses)

        self.output(results)

massgeocode = MassGeocode()
massgeocode.run()
