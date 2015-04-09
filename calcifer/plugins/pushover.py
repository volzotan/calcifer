from mainframe import *

import requests
import logging

logger = logging.getLogger(__name__)

"""
Limitations
title: 250 chars
message body: 1024 chars
"""


class Pushover(Plugin):

    TYPE_QUIET                  = -1
    TYPE_NORMAL                 =  0
    TYPE_HIGH_PRIORITY          =  1
    TYPE_REQUIRE_CONFIRMATION   =  2

    def __init__(self, config):
        logging.getLogger("requests").setLevel(logging.WARNING)

        self.api_key = config["api_key"]
        self.user_key = config["user_key"]
        self.url = config["url"]

    def deliver(self, message):
        # ignore priority
        try:
            self._send(message)
            logger.debug("delivery successful [{}]".format(message.mid))
            return Status.SENT
        except Exception as e:
            logger.warn("delivery failed", exc_info=True)
            return Status.FAILED

    def check_delivery(self, message):
        # TODO delivery checking for type_req_conf
        pass

    def _send(self, msg):
        options = { "token": self.api_key,
                    "user": self.user_key,
                    "message": msg.payload
                  }

        if msg.priority == Priority.SILENT:
            options["priority"] = self.TYPE_QUIET
        elif msg.priority == Priority.LOW:
            options["priority"] = self.TYPE_QUIET
        elif msg.priority == Priority.MEDIUM:
            options["priority"] = self.TYPE_NORMAL
        elif msg.priority == Priority.HIGH:
            # requires retry and expire params
            options["priority"] = self.TYPE_HIGH_PRIORITY

        r = requests.post(self.url, params=options)