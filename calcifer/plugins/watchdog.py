from util import *
import requests

logger = logging.getLogger(__name__)

# TODO: missing features
# POST and HEAD, rather than just GET
# JSON
# login data

class Watchdog(Plugin):
    
    def __init__(self, config):
        self.address = config["address"]

    def work(self):
        message_list = []

        try:
            r = requests.get(self.address)

            if r.status_code is not 200:
                message_list.append(self._create_message("watchdog: {} // status code: {}".format(self.name, r.status_code)))
        except requests.ConnectionError as ce:
            message_list.append(self._create_message("watchdog: {} // connection error".format(self.name)))
            logger.debug(ce)
        except Exception as e:
            raise e

        return message_list


    def _create_message(self, payload):
        message = Message(payload)
        message.mid = self.name # TODO
        message.sender = self

        message.priority = Priority.low
        return message