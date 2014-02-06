db = dict(
    HOST = "localhost",
    DATABASE = "myapp",
    USERNAME = "myapp",
    PASSWORD = "myapp",
    QUERY = "SELECT id, address, address_number, area, prefecture, postal_code FROM places WHERE status = -1",
    COLUMNS = ("id", "address", "address_number", "area", "prefecture", "postal_code"),
    COLS_EXCL_GEO = ("id")
)
