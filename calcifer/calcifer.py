import daemon
import os
import socket
import argparse
import logging

import mainframe
from util import SocketCommand, Termcolors

logger = logging.getLogger(__name__)
 
logfile = open('ccf_logfile', 'w+')
errfile = open('ccf_errfile', 'w+')

context = daemon.DaemonContext()
context.stdout = logfile
context.stderr = errfile

context.working_directory = os.path.dirname(os.path.realpath(__file__)) # script file directory
                                                                        # or working directory: os.getcwd()


def _start():
    mframe = mainframe.Mainframe()
    mframe.loop()


def debug(): # TODO benachrichtigungen abschalten
    logger.info("start in debug-mode")
    _start()


def start():
    if args.no_detach is True:
        logger.info("start in no-detach-mode")
        _start()
    else:
        logger.info("starting daemon")
        with context:
            _start()


def _send(msg):
    try:
        os.unlink("/tmp/calcifer_socket_send")
    except OSError:
        if os.path.exists("/tmp/calcifer_socket_send"):
            raise

    sock_recv = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock_send = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock_send.bind("/tmp/calcifer_socket_send")
    sock_recv.connect("/tmp/calcifer_socket_recv")
    sock_recv.send(msg)
    print sock_send.recvfrom(1024)[0]
    sock_send.close()
    sock_recv.close()


def status():
    _send(SocketCommand.STATUS)


def reload_config():
    _send(SocketCommand.RELOAD)


def stop():
    try:
        _send(SocketCommand.KILL)
    except socket.error as e:
        print(Termcolors.red("Stopping failed: ") + str(e))


#----------------------------------- argparse -----------------------------------#

parser = argparse.ArgumentParser(prog='PROG')
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
subparsers = parser.add_subparsers(help='help for subcommand')

parser_start = subparsers.add_parser('start', help='starts the daemon')
parser_start.add_argument('-nod', '--no-detach', action="store_true", help='do not detach')
parser_start.set_defaults(func=start)

parser_debug = subparsers.add_parser('debug', help='starts the daemon in debug mode')
parser_debug.set_defaults(func=debug)

parser_status = subparsers.add_parser('status', help='lay of the land')
parser_status.set_defaults(func=status)

parser_reload = subparsers.add_parser('reload', help='reload the plugin config')
parser_reload.set_defaults(func=reload_config)

parser_stop = subparsers.add_parser('stop', help='stops the daemon')
parser_stop.add_argument('-b', type=str, help='help for b')
parser_stop.add_argument('-c', type=str, action='store', default='', help='test')
parser_stop.set_defaults(func=stop)

#---------------------------------------------------------------------------------#

if __name__ == "__main__":
    args = parser.parse_args()
    args.func()