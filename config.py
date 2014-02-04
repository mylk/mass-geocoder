db = dict(
    HOST = "localhost",
    DATABASE = "myapp",
    USERNAME = "myapp",
    PASSWORD = "myapp",
    QUERY = "SELECT id, address, address_number, prefecture, postal_code FROM placesimport LIMIT 5",
    COLUMNS = ("id", "address", "address_number", "prefecture", "postal_code"),
    COLS_EXCL_GEO = ("id")
)
