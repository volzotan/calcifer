import random
import datetime
import pytz
from enum import Enum
import pickle
import json

import logging

logger = logging.getLogger(__name__)

CLEANUP_TIME = 60  # in minutes

class SocketCommand(object):
    STATUS      = "status"
    KILL        = "kill"
    RELOAD      = "reload"

class Priority(Enum):
    high        = 30
    medium      = 20
    low         = 10

    silent      = -1

class Status(Enum):
    read        = 40
    delivered   = 30
    sent        = 20
    unknown     = 0

    failed      = -10

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
    def __init__(self, payload, priority=Priority.medium, mid=None, sender=None):
        if mid is None:
            self.mid = str(random.randrange(0, 100000))
        else:
            self.mid = mid
        self.payload = payload
        self.priority = priority
        self.sender = sender

    def get_json(self):
        pass

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.mid == other.mid

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "{} {} |{}| :: {}".format(self.mid, self.priority, self.sender, self.payload[0:25])

    def __repr__(self):
        return "{} {}".format(self.__class__, self.mid)


class MessageJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Message):
            return obj.__dict__
        if isinstance(obj, Plugin):
            return [type(obj).__name__, obj.name]
        if isinstance(obj, Enum):
            return obj.name
        if isinstance(obj, datetime.datetime):
            return str(obj.astimezone(pytz.utc))

        return json.JSONEncoder.default(self, obj)


class MessageJSONDecoder(object):  # not a proper JSONDecoder
    def decode(self, obj):
        pyobj = json.loads(obj)

        priority = pyobj["priority"]
        priority = Priority[priority]

        sender = pyobj["sender"]
        # TODO: further brainwork needed

        msg = Message(pyobj["payload"], priority=priority, mid=pyobj["mid"], sender=sender)

        return msg


class Plugin(object):

    plugin_configuration = {}
    failure = None

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

    def get_generic_name(self):
        return self.__class__.__name__

    def __str__(self):
        return self.name


class Scheduler(object):

    """ TODO:

        omit multiple runs at once
    """

    def __init__(self):
        self.data = {}

    def add(self, plugin, duty_cycle):
        self.data[plugin] = [duty_cycle, datetime.datetime.now(pytz.utc) - datetime.timedelta(seconds=duty_cycle+1)]
        logger.debug("add schedule: {} -> {}".format(plugin, duty_cycle))

    def remove(self, plugin):
        if plugin in self.data:
            del self.data[plugin]
            logger.debug("removed from scheduler: {}".format(plugin))
            return True
        else:
            logger.debug("remove, but plugin not in scheduler: {}".format(plugin))
            return False

    def check(self, plugin):
        duty_cycle = self.data[plugin][0]
        last_update = self.data[plugin][1]

        if last_update < datetime.datetime.now(pytz.utc) - datetime.timedelta(seconds=duty_cycle):
            self.data[plugin][1] = last_update + datetime.timedelta(seconds=duty_cycle)
            return True
        else:
            return False

    def get_duty_cylce(self, plugin):
        if plugin in self.data:
            return self.data[plugin][0]
        else:
            return None


class Backstore(object):
    def __init__(self):
        self.data = {}

    def add(self, message, status=Status.unknown):
        if message not in self:
            tmp = {}
            tmp["message"] = message
            tmp["add_time"] = datetime.datetime.now(pytz.utc)
            tmp["update_time"] = None
            tmp["sent_status"] = status
            self.data[message.mid] = tmp
        else:
            self.data[message.mid]["message"] = message
            self.data[message.mid]["update_time"] = datetime.datetime.now(pytz.utc)

    """
        Updates the message status
    """
    def update_status(self, mid, status):
        if mid in self.data:
            self.data[mid]["update_time"] = datetime.datetime.now(pytz.utc)
            self.data[mid]["sent_status"] = status
        else:
            raise LookupError("message not in backstore")

    def remove(self, message):
        if message.mid in self.data:
            del self.data[message.mid]
            logger.debug("message removed: {}".format(message))
            return True
        else:
            logger.debug("remove non existant message: {}".format(message))
            return False

    def get(self, mid):
        try:
            return self.data[mid]["message"]
        except KeyError:
            return None

    """
        returns all stored messages (including backstore metadata)
    """
    def get_all_data(self):
        list = []
        if len(self.data) > 0:
            for _, value in self.data.iteritems():
                list.append(value)
        return list

    """
        returns all stored messages (without backstore metadata)
    """
    def get_all_messages(self):
        list = []
        if len(self.data) > 0:
            for _, value in self.data.iteritems():
                list.append(value["message"])
        return list

    def clear(self):
        logger.debug("backstore cleared")
        self.data = {}

    def empty(self):
        if len(self.data) > 0:
            return False
        else:
            return True

    def serialize(self, picklefile):
        pickle.dump(self.data, picklefile)
        logger.debug("backstore serialized to picklefile: {}".format(picklefile))

    def deserialize(self, picklefile):
        self.data = pickle.load(picklefile)
        logger.debug("loaded backstorefile: {}".format(picklefile))


    """
    Cleanup deletes every message that was not created or updated for CLEANUP_TIME minutes.
    Identical Messages which are constantly added to the backstore (e.g. Exceptions), refresh
    their update time and are not removed by cleanup.

    """

    def cleanup(self):
        counter = 0

        dellist = []

        for key, item in self.data.iteritems():
            upd = item["update_time"]
            add = item["add_time"]

            if upd is not None:
                add = upd

            if datetime.timedelta(minutes=CLEANUP_TIME) < datetime.datetime.now(pytz.utc) - add:
                dellist.append(key)

        for key in dellist:
            del self.data[key]
            counter += 1

        if counter > 0:
            logger.debug("backstore cleanup: {} messages".format(counter))

        return counter

    def __contains__(self, message):
        if message.mid in self.data:
            return True
        else:
            return False

    def __str__(self):
        status_read = 0
        status_delivered = 0
        status_sent = 0
        status_unknown = 0
        status_failed = 0

        # TODO: don't use mid, it contains no user readable information

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

            age = datetime.datetime.now(pytz.utc) - item["add_time"]
            age = age.total_seconds() / 60
            age = int(age)

            if status == Status.read:
                status_read += 1
                status = "READ"
            elif status == Status.delivered:
                status_delivered += 1
                status = "DLVRD"
            elif status == Status.sent:
                status_sent += 1
                status = "SENT"
            elif status == Status.unknown:
                status_unknown += 1
                status = "UNKNWN"
            elif status == Status.failed:
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

        if counter == 0:
            tmp = "EMPTY"

        return rval + tmp

