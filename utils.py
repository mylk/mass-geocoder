from string import ascii_lowercase, ascii_uppercase, digits
from hashlib import sha1
from random import choice
from datetime import datetime

class errorLevels:
    ERROR = "Error"
    WARN = "Warning"

class utils:
    def __init__(self):
        pass
    
    def generate_unique_str(self, length):
        unique = ""
        charRange = ascii_lowercase + ascii_uppercase + digits

        for x in range(length):
            unique += choice(charRange)

        return unique

    def generate_SHA1(self, length):
        # feed with rand str by exec generateUniqueStr(len)
        return sha1(self.generate_unique_str(24)).hexdigest()[0:length]

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
        if level == errorLevels.ERROR:
            # just exiting with any other than 0, just to be catchable by the os/other scripts
            exit(1);

    def encode_data(self, data):
        if type(data) is long:
            return str(data)
        elif type(data) is str:
            return data.encode("utf-8")
        else:
            return data

    def get_empty(self, value):
        if value == None:
            return ""
        else:
            return value

    def right_now(self):
        return str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
