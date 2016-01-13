from util import *

import imaplib
from email.parser import HeaderParser
from email import header
import logging
import re
import fnmatch

logger = logging.getLogger(__name__)

class Mail(Plugin):

    def __init__(self, config):
        self.imap_server = config["imap_server"]
        self.address = config["mailaddress"]

        self.username = None
        try:
            if config["username"] is not None:
                self.username = config["username"]
        except:
            pass

        self.password = config["imap_password"]
        self.folder = config["folder"]
        self.watchlist = config["watchlist"]

    def _connect(self):
        self.imap = imaplib.IMAP4_SSL(self.imap_server)
        if self.username is not None:
            self.imap.login(self.username, self.password)
        else:
            self.imap.login(self.address, self.password)
        self.imap.select(self.folder, readonly=True)

    def _close(self):
        if self.imap is not None:
            self.imap.close()
            self.imap.logout()

    def work(self):
        self._connect()

        message_list = []

        (type, data) = self.imap.search(None, 'UNSEEN')
        if type == "OK":
            if data[0] is not None:
                for num in (data[0].split()):
                    (type, data) = self.imap.fetch(num, '(BODY[HEADER.FIELDS (SUBJECT FROM MESSAGE-ID)])')
                    mailbody = data[0][1]

                    headers = HeaderParser().parsestr(mailbody)

                    address = re.findall("<(.*)>", headers["from"])
                    if len(address) == 0:
                        address = headers["from"]
                    else:
                        address = address[0]

                    subject = headers["subject"]

                    # deal with base64 encoded UTF-8 strings (e.g. =?UTF-8?B?1av3 )
                    # deal with quoted printable UTF-8 strings (e.g. =?UTF-8?Q?foo? )
                    subject = header.decode_header(subject)[0][0]

                    message = Message("{} : {}".format(address, subject))
                    message.mid = headers["message-id"][1:-1]
                    message.sender = self

                    message.priority = Priority.low
                    for elem in self.watchlist:
                        if fnmatch.fnmatch(address, elem): # shell like globbing
                            message.priority = Priority.medium

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