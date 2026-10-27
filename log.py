"""Logging utility for the add-in."""
import io
import time
from common import path_from_add_on

class Logging:
    def __init__(self, log_file_name="log.txt"):
        self.log_file_path = path_from_add_on(log_file_name)
        self.log_file = io.FileIO(self.log_file_path, "a")
        self.write("Log started at {}", time.strftime("%Y-%m-%d %H:%M:%S"))

    @staticmethod
    def _format_message(message, *args, **kwargs):
        try:
            return message.format(*args, **kwargs)
        except Exception:
            try:
                if args:
                    return message % args
            except Exception:
                pass
            return f"{message} {args} {kwargs}"

    def write(self, message, *args, **kwargs):
        if self.log_file:
            formatted_message = time.strftime("%Y-%m-%d %H:%M:%S") + ": " + self._format_message(message, *args, **kwargs)
            self.log_file.write(formatted_message.encode("utf-8"))
            self.log_file.write(b"\n")
            self.log_file.flush()

    def write_error(self, message, *args, **kwargs):
        if self.log_file:
            formatted = self._format_message(message, *args, **kwargs)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"{timestamp}: Error: {formatted}\n".encode("utf-8"))
            self.log_file.flush()

    def writeError(self, message, *args, **kwargs):
        self.write_error(message, *args, **kwargs)

    def close(self):
        if self.log_file:
            self.log_file.close()
            self.log_file = None

log = Logging()
