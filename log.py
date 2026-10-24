"""Logging utility for the add-in."""
import io
import time
from common import path_from_add_on

class Logging:
    def __init__(self, log_file_name="log.txt"):
        self.log_file_path = path_from_add_on(log_file_name)
        self.log_file = io.FileIO(self.log_file_path, "a")
        self.write("Log started at {}", time.strftime("%Y-%m-%d %H:%M:%S"))

    def write(self, message, *args):
        if self.log_file:
            formatted_message = time.strftime("%Y-%m-%d %H:%M:%S") + ": " + message.format(*args)
            self.log_file.write(formatted_message.encode("utf-8"))
            self.log_file.write(b"\n")

    def writeError(self, message, *args):
        if self.log_file:
            formatted_message = time.strftime("%Y-%m-%d %H:%M:%S") + ": Error:" + message.format(*args)
            self.log_file.write(formatted_message.encode("utf-8"))
            self.log_file.write(b"\n")

    def close(self):
        if self.log_file:
            self.log_file.close()
            self.log_file = None

log = Logging()
