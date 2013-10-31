#!/usr/bin/python
# -*- coding: utf8 -*-

from urllib2 import urlopen
from urllib import quote_plus
from json import loads
from string import ascii_lowercase, ascii_uppercase, digits
from hashlib import sha1
from random import choice
from sys import argv

def generate_unique_str(length):
	unique = ""
	charRange = ascii_lowercase + ascii_uppercase + digits

	for x in range(length):
		unique += choice(charRange)

	return unique

def generate_SHA1(length):
	# feed with rand str by exec generateUniqueStr(len)
	return sha1(generate_unique_str(24)).hexdigest()[0:length]

def help():
        print """
        Mass geocoder

        This tools mass geocodes using the Google Maps API,
        and produces SQL insert statements.

        Usage:
        massgeocode.py addresses_file

        It's recommended that the file has the following structure:
        - One address per line
        - Each line has the following information:
            email;fullAddress

            Full address is recommended to be formatted as follows:
            street streetNumber city postalCode
        """

def main():
    if len(argv) == 1 or argv[1] == "-h" or argv[1] == "--help":
        help()
        exit()

    file = open(argv[1], "r")
    addresses = file.read()
    addressesSplit = addresses.splitlines()

    for address in addressesSplit:
        # url encode address

        addressSplit = address.split(";")
        email = addressSplit[0]
        address = addressSplit[1]
        
        request = urlopen("http://maps.googleapis.com/maps/api/geocode/json?sensor=false&language=el&address=" + quote_plus(address))
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

            print "INSERT INTO places (email, uniqueid, category_id, address, city, prefecture, area, postal_code, lat, lng, phone_number, created_at) VALUES ('" + email + "', '" + uniqueid + "', 1, TRIM('" + street + " " + streetNumber + "'), '" + city + "', '" + prefecture + "', '" + prefecture + "', '" + postalCode + "', '" + lat + "', '" + lat + "', '', CONCAT(CURRENT_DATE, ' ', CURRENT_TIME));"
        else:
            print "Error " + response["status"]

    file.close()

main()