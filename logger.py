""" logging module """
import sys
import json
import logging

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        return json.dumps(log_entry)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
