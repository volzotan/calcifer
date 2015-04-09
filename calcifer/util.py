import random
import datetime

import logging

logger = logging.getLogger(__name__)

CLEANUP_TIME = 60  # in minutes

class SocketCommand(object):
    STATUS      = "status"
    KILL        = "kill"
    RELOAD      = "reload"

class Priority(object):
    HIGH        = 30
    MEDIUM      = 20
    LOW         = 10

    SILENT      = -1

class Status(object):
    READ        = 40
    DELIVERED   = 30
    SENT        = 20
    UNKNOWN     = 0

    FAILED      = -10

class Termcolors(object):
    RESET       = '\033[0m'

    RED         = '\033[91m'
    GREEN       = '\033[92m'
    WARNING     = '\033[93m'
    BLUE        = '\033[94m'

    HEADER      = '\033[95m'

    BOLD        = '\033[1m'
    UNDERLINE   = '\033[4m'

    @staticmethod
    def red(inp):
        return Termcolors.RED + inp + Termcolors.RESET

    @staticmethod
    def green(inp):
        return Termcolors.GREEN + inp + Termcolors.RESET


class Message(object):
    def __init__(self, payload, priority=Priority.MEDIUM, mid=None, sender=None):
        if mid is None:
            self.mid = str(random.randrange(0, 100000))
        else:
            self.mid = mid
        self.payload = payload
        self.priority = priority
        self.sender = sender

    def __str__(self):
        return "{} {} |{}| :: {}".format(self.mid, self.priority, self.sender, self.payload[0:25])

    def __repr__(self):
        return self.__str__()


class Plugin(object):

    plugin_configuration = {}

    def __init__(self, config):
        pass

    def work(self):
        return []

    def deliver(self, message):
        pass

    def check_delivery(self, message):
        pass

    def close(self):
        pass

    def __str__(self):
        return self.name


class Scheduler(object):
    def __init__(self):
        self.data = {}

    def add(self, plugin, duty_cycle):
        self.data[plugin] = [duty_cycle, datetime.datetime.now() - datetime.timedelta(seconds=duty_cycle+1)]
        logger.debug("add schedule: {} -> {}".format(plugin, duty_cycle))

    def remove(self, plugin):
        if plugin in self.data:
            del self.data[plugin]
            return True
        else:
            return False

    def check(self, plugin):
        duty_cycle = self.data[plugin][0]
        last_update = self.data[plugin][1]

        if last_update < datetime.datetime.now() - datetime.timedelta(seconds=duty_cycle):
            self.data[plugin][1] = last_update + datetime.timedelta(seconds=duty_cycle)
            return True
        else:
            return False


class Backstore(object):
    def __init__(self):
        self.data = {}

    def add(self, message, status=Status.UNKNOWN):
        if message.mid not in self.data:
            tmp = {}
            tmp["message"] = message
            tmp["add_time"] = datetime.datetime.now()
            tmp["update_time"] = None
            tmp["sent_status"] = status
            self.data[message.mid] = tmp
        else:
            self.data[message.mid]["message"] = message
            self.data[message.mid]["update_time"] = datetime.datetime.now()

    """
        Updates the message status too
        while /add/ ignores status when a duplicate message is added
    """
    def update(self, message, status):
        self.data[message.mid]["message"] = message
        self.data[message.mid]["update_time"] = datetime.datetime.now()
        self.data[message.mid]["sent_status"] = status

    def remove(self, message):
        if message.mid in self.data:
            del self.data[message.mid]
            return True
        else:
            return False

    def get(self, message):
        return self.data[message.mid]

    def get_all(self):
        list = []
        if len(self.data) > 0:
            for _, value in self.data.iteritems():
                list.append(value)
        return list

    def contains(self, message):
        if message.mid in self.data:
            return True
        else:
            return False

    def empty(self):
        if len(self.data) > 0:
            return False
        else:
            return True

    """
    Cleanup deletes every message that was not created or updated for CLEANUP_TIME minutes.
    Identical Messages which are constantly added to the backstore (e.g. Exceptions), refresh
    their update time and are not removed by cleanup.

    """

    def cleanup(self):
        counter = 0

        for _, item in self.data.iteritems():
            upd = item["update_time"]
            add = item["add_time"]

            if upd is not None:
                add = upd

            if datetime.timedelta(minutes=CLEANUP_TIME) < datetime.datetime.now() - add:
                del item
                counter += 1

        if counter > 0:
            logger.debug("backstore cleanup: {} messages".format(counter))

        return counter

    def __repr__(self):
        status_read = 0
        status_delivered = 0
        status_sent = 0
        status_unknown = 0
        status_failed = 0

        tmp = ""
        template = "{0:>3d}|from: {1:<30s} |id: {2:<30s} |length: {3:>4d} |age: {4:>3d} |status: {5:>3s}\n"

        counter = 0
        for entry in self.data.iteritems():
            item = entry[1]

            counter = counter+1
            index = counter

            sender = item["message"].sender
            mid = item["message"].mid[0:30]
            length = len(item["message"].payload)
            status = item["sent_status"]

            age = datetime.datetime.now() - item["add_time"]
            age = age.total_seconds() / 60
            age = int(age)

            if status == Status.READ:
                status_read += 1
                status = "READ"
            elif status == Status.DELIVERED:
                status_delivered += 1
                status = "DLVRD"
            elif status == Status.SENT:
                status_sent += 1
                status = "SENT"
            elif status == Status.UNKNOWN:
                status_unknown += 1
                status = "UNKNWN"
            elif status == Status.FAILED:
                status_failed += 1
                status = "FAILED"

            tmp += template.format(index, sender, mid, length, age, status)

        rval =  "backlog : "
        rval += "READ:  {0:2d}  "
        rval += "DELIVERED:  " + Termcolors.GREEN + "{1:2d}" + Termcolors.RESET + "  "
        rval += "SENT:  {2:2d}  "
        rval += "UNKNOWN:  {3:2d}  "
        rval += "FAILED:  " + Termcolors.RED + "{4:2d}" + Termcolors.RESET + "  "
        rval += "->  all:  {5:3d}\n"
        rval = rval.format(status_read, status_delivered, status_sent, status_unknown, status_failed, len(self.data))

        return rval + tmp
