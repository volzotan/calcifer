import daemon
import os
import socket
import argparse
import sys
import logging

import mainframe
from util import SocketCommand, Termcolors

logger = logging.getLogger(__name__)
 
logfile = open('ccf_logfile', 'a+')
errfile = open('ccf_errfile', 'a+')

context = daemon.DaemonContext()
context.stdout = logfile
context.stderr = errfile

context.working_directory = os.path.dirname(os.path.realpath(__file__)) # script file directory
                                                                        # or working directory: os.getcwd()


def _start(params):
    mframe = mainframe.Mainframe(params)
    mframe.loop()


def start():
    start_params = {}

    if args.debug is True:
        logger.info("start in debug-mode")
        start_params["debug"] = True

    if args.cork is True:
        logger.info("cork enabled")
        start_params["cork"] = True

    if args.backstorefile:
        logger.info("loading backstore pickle")
        try:
            picklefile = open(args.backstorefile)
            start_params["backstore_pickle"] = picklefile
        except Exception as e:
            logger.warn("loading backstorefile failed", exc_info=True)
            sys.exit(-1)

    if args.no_detach is True:
        logger.info("start in no-detach-mode")
        _start(start_params)
    else:
        logger.info("starting daemon")

        with context:
            _start(start_params)


def _send(msg):
    try:
        os.unlink("/tmp/calcifer_socket_send")
    except OSError:
        if os.path.exists("/tmp/calcifer_socket_send"):
            raise

    # TODO: don't use datagrams

    sock_recv = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock_send = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock_send.bind("/tmp/calcifer_socket_send")
    sock_recv.connect("/tmp/calcifer_socket_recv")
    sock_recv.send(msg)
    print("")
    print(sock_send.recvfrom(1024)[0])
    print("")
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

def build_parser():

    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    subparsers = parser.add_subparsers(help='help for subcommand')

    parser_start = subparsers.add_parser('start', help='starts the daemon')

    parser_start.add_argument('-nod', '--no-detach',
                              action="store_true",
                              help='do not detach')

    parser_start.add_argument('-d', '--debug',
                              action="store_true",
                              help='debug mode')

    parser_start.add_argument('-c', '--cork',
                              action="store_true",
                              help='cork. enables REST API and starts werkzeug server')

    parser_start.add_argument('-f', '--backstorefile',
                              help='load a serialized backstore') # TODO wrong argument type

    parser_start.set_defaults(func=start)

    parser_status = subparsers.add_parser('status', help='lay of the land')
    parser_status.set_defaults(func=status)

    parser_reload = subparsers.add_parser('reload', help='reload the plugin config')
    parser_reload.set_defaults(func=reload_config)

    parser_stop = subparsers.add_parser('stop', help='stops the daemon')
    parser_stop.add_argument('-b', type=str, help='help for b')
    parser_stop.add_argument('-c', type=str, action='store', default='', help='test')
    parser_stop.set_defaults(func=stop)

    return parser

#---------------------------------------------------------------------------------#

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(message)s')

    args = build_parser().parse_args()
    args.func()