#!/usr/bin/python
# -*- coding: utf8 -*-

from sys import exc_info, path
import urllib2
from urllib import quote_plus
from json import loads
from MySQLdb import connect
from os import access, R_OK
from argparse import ArgumentParser, Action, RawTextHelpFormatter
import config # geocoding configuration file
from utils import Utils, ErrorLevels

utils = Utils()
errorLevels = ErrorLevels()
__version__ = "1.1"

# used in argsparse
args = ()
# stores exluded columns and their values from geocoding, for later use
geo_excluded = {}
# stores profile object
profile = {}
# ugly hack to let the secondary queries to execute
_addresses = []
# ugly hack to keep the index of the last query executed
_addressIndex = 0
# http proxy handler
proxy = ""



# custom argsparse action
class ArgsDeps(Action):
    def __call__(self, parser, args, values, option = None):
        args.method = values

        if args.method == "file" and not args.file:
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
        proxy = urllib2.ProxyHandler({"http": "my.proxy.com:8080"})
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)
        self.setup_args()

    def setup_args(self):
        global args

        help_descr = self.help()
        argparser = ArgumentParser(description=help_descr, formatter_class=RawTextHelpFormatter)
        argparser.add_argument("-p", "--profile", help="The application profile.", required=True, action=LoadProfile)
        argparser.add_argument("-f", "--file", help="The file that contains the addresses to be queried.", required=False)
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
            file = args.file
            addresses = []

            # check if file exists and access rights are ok
            if access(file, R_OK):
                file = open(file, "r")
                addressesfile = file.read().decode("utf-8")

                # break the row to columns
                for _row in addressesfile.splitlines():
                    addresses.append(_row.split(";"))

                    queryResults.append(dict(
                        address = _row[0],
                        area = _row[1],
                        city = _row[2],
                        prefecture = _row[3],
                        postal_code = _row[4]
                    ))

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

    # fill the queries with the required data
    def prepare_insert(self, input_data, result):
        return profile.db["TEMPLATE_INSERT"] % (input_data["address"] or result["address"], input_data["area"] or result["area"], input_data["city"] or result["city"], input_data["prefecture"] or result["prefecture"], input_data["postal_code"] or result["postal_code"], result["lat"], result["lng"])

    def prepare_update(self, input_data, result):
        return profile.db["TEMPLATE_UPDATE"] % (result["lat"], result["lng"], input_data["address"], input_data["area"], input_data["city"], input_data["prefecture"], input_data["postal_code"])

    def output(self, result):
        queries = []

        if args.inserts and not args.updates:
            query = self.prepare_insert(input_data, result)
        elif args.updates:
            query = self.prepare_update(input_data, result)

        if args.dump and not args.force:
            print query
        elif args.force:
            try:
                con = connect(host=profile.db["HOST"], user=profile.db["USERNAME"], passwd=profile.db["PASSWORD"], db=profile.db["DATABASE"], charset="utf8")
            except:
                utils.log(exc_info(), errorLevels.ERROR)

            cur = con.cursor()
            cur.execute(query)
            cur.close()
            con.commit()
            con.close()

    def geocode(self, address, rowId, retry = False):
        try:
            request = urllib2.urlopen(u"http://maps.googleapis.com/maps/api/geocode/json?sensor=false&language=" + config.geocode["LANGUAGE"] + u"&region=" + config.geocode["REGION"] + u"&address=" + quote_plus(address))
        except:
            utils.log(exc_info(), errorLevels.ERROR)

        # json.loads()
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

                    return dict(
                        row_id = rowId,
                        uniqueid = uniqueid,
                        address = "TRIM('" + street + " " + streetNumber + "')",
                        city = city,
                        prefecture = prefecture,
                        area = area,
                        postal_code = postalCode,
                        lat = lat,
                        lng = lng,
                        created_at = utils.right_now()
                    )
            #else:
            #    return dict(error = response["status"])
        else:
            return dict(error = response["status"])

    def help(self):
        return """
         -Mass geocoder

        This tool mass geocodes using the Google Maps API,
        and produces SQL statements.

        The input method can be any of the below:
        - db
            Database connection configuration will be retrieved
            from the profile specified, placed in the "profiles" directory.
        - file
            It's recommended that the file has the following structure:
            - One address per line,
            - Each line has the following information:
                address area city prefecture postalCode
            - The fields above, have to be seperated by semicolumns ";".
        """

    def run(self):
        addresses = self.get_addresses()
        addressIndex = 0
        rowId = 0

        for address in addresses[0]:
            queryIndex = 0

            if args.method == "db":
                rowId = str(geo_excluded[profile.db["ROW_IDENTIFIER"]][addressIndex])
            else:
                rowId = address[0]
            result = dict()

            while ("error" in result or len(result) == 0):
                address = " ".join(addresses[queryIndex][addressIndex]).encode("utf8")

                result = self.geocode(address, rowId)

                if "error" in result and result["error"] == "ZERO_RESULTS":
                    utils.log("Error " + result["error"] + " for address: " + address.decode("utf8"), errorLevels.WARN)

                    if len(addresses) - 1 > queryIndex:
                        queryIndex += 1
                    else:
                        break
            else:
                self.output(result)

            addressIndex += 1

massgeocode = MassGeocode()
massgeocode.run()
