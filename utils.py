from datetime import datetime

# just enum error levels
class ErrorLevels:
    ERROR = "Error"
    WARN = "Warning"

class Utils:
    def __init__(self):
        pass

    def log(self, error, level):
        now =  datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # check if error object passed or just string
        if type(error) is tuple:
            if error[0].__name__ == "KeyboardInterrupt":
                errorDesc = "Interrupted by the user."
            else:
               errorDesc = str(error[0].__name__) + ", " + str(error[1])
        else:
            errorDesc = error

        print errorDesc

        # append error to error log file
        f = open("error.log", "ab")
        f.write("" + now + "\t" + level + "\t\t" + errorDesc.encode("utf-8").replace(", ", "\t") + "\n")
        f.close()

        # exiting on "error" error level
        if level == ErrorLevels.ERROR:
            # just exiting with any other than 0, just to be catchable by the os/other scripts
            exit(1);

    def geoloc_in_range(self, lat, lng, address):
        try:
            if (float(lat) > 33.329890114795035 and float(lat) < 43.936911706744986 and
               float(lng) > 14.353004693984985 and float(lng) < 35.380836725234985) or \
               (float(lat) > 34.41128705078732 and float(lat) < 35.80429713948756 and
               float(lng) > 32.0522051284413 and float(lng) < 34.68068413234755):
                return True
            else:
                self.log("Latitude or longitude values [" + str(lat) + "," + str(lng) + "] are INVALID (out of range). {query = '" + address + "'}...", ErrorLevels.WARN)
                return False
        except:
            self.log(exc_info(), ErrorLevels.WARN)
            return False