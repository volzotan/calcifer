import socket
import sys
import os
import logging

import threading

logger = logging.getLogger(__name__)

socket_address_recv = "/tmp/calcifer_socket_recv"
socket_address_send = "/tmp/calcifer_socket_send"


class SocketManager(object):

    def __init__(self, q):
        self.queue = q

        try:
            os.unlink(socket_address_recv)
        except OSError:
            if os.path.exists(socket_address_recv):
                raise

        try:
            os.unlink(socket_address_send)
        except OSError:
            if os.path.exists(socket_address_send):
                raise

        self.sock_recv = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        # self.sock_recv.settimeout(1)
        self.sock_recv.bind(socket_address_recv)

        self.sock_send = None

        t = threading.Thread(target=self.receive)
        t.daemon = True
        t.start()


    def receive(self):
        logger.info("receive thread started")

        while True:
            self.queue.put(self.sock_recv.recv(1024))


    def send(self, data):
        logger.debug("send: [{}]".format(data))
        self.sock_send = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock_send.connect(socket_address_send)
        self.sock_send.sendall(data)
        self.sock_send.close()


    def close(self):
        if not self.sock_send is None:
            self.sock_send.close()

        if not self.sock_recv is None:
            self.sock_recv.close()
