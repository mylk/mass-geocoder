#!/usr/bin/python2
# -*- coding: utf8 -*-

from sys import exc_info, path
import urllib2
from urllib import quote_plus
from json import loads
from MySQLdb import connect
from os import access, R_OK
from argparse import ArgumentParser, Action, RawTextHelpFormatter
from utils import Utils, ErrorLevels

utils = Utils()
errorLevels = ErrorLevels()
__version__ = "1.1"

# used in argsparse
args = ()
# stores profile object
profile = {}

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
        # append profiles subdir to the path variable, so we can import dynamically the profile file
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
        argparser.add_argument("-p", "--profile", help="The application profile, containing format of queries and DB connection info", required=True, action=LoadProfile)
        argparser.add_argument("-f", "--file", help="The file that contains the addresses to be geocoded.", required=False)
        argparser.add_argument("-m", "--method", help="The method that the addresses will be retrieved.", required=True, action=ArgsDeps)
        argparser.add_argument("--force", help="Queries will be executed to the database.", action="store_true", default=False)
        argparser.add_argument("--dump", help="Queries will be dumped in the terminal session.", action="store_true", default=True)
        argparser.add_argument("--inserts", help="The type of statements that the application will produce.", action="store_true", default=True)
        argparser.add_argument("--updates", help="The type of statements that the application will produce.", action="store_true", default=False)
        argparser.add_argument("--proxy", help="The address and port of the proxy server to be used.", default=False)

        args = argparser.parse_args()

    def get_addresses(self):
        results = []

        if args.method == "file":
            # check if file exists and access rights are ok
            if access(args.file, R_OK):
                file = open(args.file, "r")
                addresses = file.read().decode("utf-8")

                # break the row to columns
                for _row in addresses.splitlines():
                    _row = _row.split(";")

                    results.append(dict(
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
            cur.execute(profile.db["QUERY"])

            for _row in cur.fetchall():
                # sanitize null values
                _row = ["" if val is None else val for val in _row]

                results.append(dict(
                    address = _row[0],
                    area = _row[1],
                    city = _row[2],
                    prefecture = _row[3],
                    postal_code = _row[4]
                ))

            cur.close()
            con.close()
        else:
            utils.log("Invalid method.", errorLevels.ERROR);

        # print repr(results).decode('raw_unicode_escape')

        return results

    def parse_geocode(self, response, address):
        street = streetNumber = city = area = prefecture = postalCode = lat = lng = ""

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
            # in_range = utils.geoloc_in_range(lat, lng, address)
            in_range = True

            if(in_range):
                return dict(
                    address = street + " " + streetNumber,
                    city = city,
                    prefecture = prefecture,
                    area = area,
                    postal_code = postalCode,
                    lat = lat,
                    lng = lng,
                )
        else:
           return dict(error = response["status"])

    def geocode(self, address):
        # http proxy handler
        proxy = None

        if args.proxy:
            proxy = urllib2.ProxyHandler({"http": args.proxy})
            opener = urllib2.build_opener(proxy)
            urllib2.install_opener(opener)

        try:
            request = urllib2.urlopen(u"http://maps.googleapis.com/maps/api/geocode/json?sensor=false&language=" + profile.locale["LANGUAGE"] + u"&region=" + profile.locale["REGION"] + u"&address=" + quote_plus(address))
        except:
            utils.log(exc_info(), errorLevels.ERROR)

        # json.loads()
        response = loads(request.read())

        if response["status"] == "OK":
            return self.parse_geocode(response, address)
        else:
            return dict(error = response["status"])

    # fill the queries with the required data
    def prepare_insert(self, input_data, result):
        return profile.db["TEMPLATE_INSERT"] % (input_data["address"] or result["address"], input_data["area"] or result["area"], input_data["city"] or result["city"], input_data["prefecture"] or result["prefecture"], input_data["postal_code"] or result["postal_code"], result["lat"], result["lng"])

    def prepare_update(self, input_data, result):
        return profile.db["TEMPLATE_UPDATE"] % (result["lat"], result["lng"], input_data["address"], input_data["area"], input_data["city"], input_data["prefecture"], input_data["postal_code"])

    def output(self, input_data, result):
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

    def run(self):
        addresses = self.get_addresses()

        for address in addresses:
            result = dict()
            addressStr = address["address"].encode("utf8") + " " + address["area"].encode("utf8") + " " + address["city"].encode("utf8") + " " + address["prefecture"].encode("utf8") + " " + address["postal_code"].encode("utf8")
            result = self.geocode(addressStr)

            if "error" in result and result["error"] == "ZERO_RESULTS":
                utils.log("Error " + result["error"] + " for address: " + addressStr.decode("utf8"), errorLevels.WARN)
            elif "error" in result:
                utils.log("Error " + result["error"], errorLevels.ERROR)
            else:
                self.output(address, result)

    def help(self):
        return """
        Mass geocoder

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

massgeocode = MassGeocode()
massgeocode.run()
