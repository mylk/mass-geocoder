# -*- coding: utf8 -*-

db = dict(
    HOST = "localhost",
    DATABASE = "placesdb",
    USERNAME = "root",
    PASSWORD = "toor",

    # queries that their data will be geocoded. each will be used if previous has failed geocoding
    QUERY = "SELECT address, address_number, area, postal_code, lat, lng FROM places WHERE lat = 0 AND lng = 0",

    # the result query template for inserts and updates
    TEMPLATE_INSERT = u"INSERT INTO places (address, area, city, prefecture, postal_code, lat, lng) VALUES ('%s', '%s', '%s', '%s', '%s', %s, %s);",
    TEMPLATE_UPDATE = u"UPDATE places SET lat = %s, lng = %s WHERE address = '%s' AND area = '%s' AND city = '%s' AND prefecture = '%s' AND postal_code = '%s';"
)