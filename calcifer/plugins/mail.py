from util import *

import imaplib
from email.parser import HeaderParser
import logging
import re
import quopri

logger = logging.getLogger(__name__)

class Mail(Plugin):

    def __init__(self, config):
        self.imap_server = config["imap_server"]
        self.address = config["mailaddress"]
        self.password = config["imap_password"]
        self.folder = config["folder"]
        self.watchlist = config["watchlist"]

    def _connect(self):
        self.imap = imaplib.IMAP4_SSL(self.imap_server)
        self.imap.login(self.address, self.password)
        self.imap.select(self.folder)

    def _close(self):
        if self.imap is not None:
            self.imap.close()
            self.imap.logout()

    def work(self):
        self._connect()

        message_list = []

        (type, data) = self.imap.search(None, '(UNSEEN)')
        if type == "OK":
            if data[0] is not None:
                for num in (data[0].split()):
                    (type, data) = self.imap.fetch(num, '(RFC822)')
                    mailbody = data[0][1]

                    headers = HeaderParser().parsestr(mailbody)

                    address = re.findall("<(.*)>", headers["from"])
                    if len(address) == 0:
                        address = headers["from"]
                    else:
                        address = address[0]

                    # deal with quoted printable UTF-8 strings (e.g. =?UTF-8?Q?foo? )
                    subject = headers["subject"]
                    subject = quopri.decodestring(subject)

                    if subject.upper().startswith("=?UTF-8?Q?"):
                        subject = subject[10:]  # remove =?UTF-8?Q?
                        subject = subject[:-1]  # remove trailing '?'

                    # deal with base64 encoded UTF-8 strings (e.g. =?UTF-8?B?1av3 )
                    if subject.upper().startswith("=?UTF-8?B?"):
                        # TODO
                        pass

                    message = Message("{} : {}".format(address, subject))
                    message.mid = headers["message-id"][1:-1]
                    message.sender = self

                    if address in self.watchlist:
                        message.priority = Priority.medium
                    else:
                        message.priority = Priority.low

                    message_list.append(message)
            else:
                # logger.debug("{}: empty imap response".format(self.name))
                pass
        else:
            logger.debug("{}: non OK imap response [type: {}]".format(self.name, type))

        self._close()
        return message_list


    def deliver(self, message):
        pass


    def check_delivery(self, message):
        pass