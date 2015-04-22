import pkgutil
import importlib
import sys
import time

from os import listdir
from os.path import isfile, join

import json
import logging
import threading
from Queue import Queue

from util import *
from socketManager import SocketManager
from web import cork

logger = logging.getLogger(__name__)

DIRECTORY = "plugins"
PACKAGE = "calcifer"
SLEEP_DURATION = 1  # in sec

class Mainframe(object):

    """params:

    debug:          sets logging level to debug and prevents that deliver() is called on plugins
    logging_level:  sets logging level (overwrites debug)

    """

    def __init__(self, params):

        if "debug" in params and params["debug"] is True:
            self.debug = True
            logging_level = logging.DEBUG
        else:
            self.debug = False

        if "logging_level" in params:
            self.logging_level = params["logging_level"]
        else:
            self.logging_level = logging.INFO

        logging.basicConfig(level=self.logging_level,
                            format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
                            datefmt='%m-%d %H:%M')

        self.backstore = Backstore()

        if "backstore_pickle" in params:
            try:
                self.backstore.deserialize(params["backstore_pickle"])
            except Exception as e:
                logger.warn("deserializing backstorefile failed", exc_info=True)

        self.plugins = []
        self.plugin_scheduler = Scheduler()

        self.message_queue = Queue()
        self.startup()

        self.socket_queue = Queue()
        self.socketManager = SocketManager(self.socket_queue)


    def __str__(self):
        return "mainframe"


    def startup(self):
        logger.info("Mainframe Startup")

        try:
            self.load_all_modules_from_dir(DIRECTORY, PACKAGE)
        except Exception:
            logger.warn("loading plugins failed", exc_info=True)

        # self.register_handlers()

        cork.mainframe = self
        t = threading.Thread(target=cork.app.run)
        t.daemon = True
        t.start()


    def reload(self):
        self.plugins = []
        self.plugin_scheduler = Scheduler()
        self.load_all_modules_from_dir(DIRECTORY, PACKAGE)


    def shutdown(self):
        logger.info("Mainframe Shutdown")

        for elem in self.plugins:
            elem.close()

        self.socketManager.close()


    # TODO: dir plugins is not relative to mainframe.py path (bug e.g. python calcifer/calcifer.py)
    def load_all_modules_from_dir(self, dirname, packagename):

        try:
            importlib.import_module(dirname)
        except ImportError: # if relative import fails due to exec from diff dir
            dirname = "." + dirname
            importlib.import_module(dirname, package=packagename)

        for importer, package_name, _ in pkgutil.iter_modules([dirname]):
            full_package_name = '%s.%s' % (dirname, package_name)
            if full_package_name not in sys.modules:
                module = importer.find_module(package_name).load_module(full_package_name)
                
                class_object = getattr(module, str(module.__name__).split('.')[-1].title())

                # check if config file(s) exits

                files_in_dir = [f for f in listdir(dirname) if isfile(join(dirname, f))]
                configfilenames = [f for f in files_in_dir if f.endswith(".config")]
                pkg_configfilenames = [f for f in configfilenames if f.startswith(package_name)]

                logger.debug("found configs: " + str(pkg_configfilenames))

                configdictlist = []
                if len(pkg_configfilenames) == 0: # use default config

                    config = {  "name": package_name,
                                "work_schedule": 60,
                                "notify_on_error": 1,
                                "plugin_settings": {}
                              }
                    configdictlist.append(config)
                else:
                    for fname in pkg_configfilenames:
                        configdictlist.append(json.load(open(join(dirname, fname))))

                # and create class instance for every config file

                for conf in configdictlist:
                    try:
                        plugin_conf = conf["plugin_settings"]
                        class_instance = class_object(plugin_conf)
                        class_instance.name = conf["name"]
                        class_instance.plugin_configuration = conf
                        self.plugins.append(class_instance)
                        self.plugin_scheduler.add(class_instance, conf["work_schedule"])

                        logger.info("imported plugin {0} as {1}".format(class_object, conf["name"]))
                    except KeyError as e:
                        logger.error("importing plugin {0} failed, incompatible configuration".format(class_object))
                    except Exception as e:
                        logger.error("importing plugin {0} failed".format(class_object), exc_info=True)
                        if class_instance.plugin_configuration["notify_on_error"]:
                            pass
                            # TODO: create message

        logger.info("imported {} plugins".format(len(self.plugins)))


    def register_handlers(self):
        for elem in self.plugins:
            self.handlers.append(elem.work)


    def loop(self):
        logger.info("event loop started")

        while True:
            try:
                self.check_plugins()

                self.check_messages()
                self.check_socket()

                self.backstore.cleanup()

                time.sleep(SLEEP_DURATION)
            except KeyboardInterrupt:
                self.shutdown()
                sys.exit(0)
            except Exception as e:
                logger.error(e, exc_info=True)
                self.shutdown()
                sys.exit(1)


    def check_plugins(self):
        for plug in self.plugins:
            if self.plugin_scheduler.check(plug):
                logger.debug("running: {}".format(plug))

                t = threading.Thread(target=self.plugin_worker, args=(self.message_queue, plug))
                t.daemon = True
                t.start()

        while not self.message_queue.empty():
            wrapper = self.message_queue.get()
            plugin = wrapper[0]
            msg = wrapper[1]

            if not isinstance(msg, Exception):
                if not self.backstore.contains(msg):
                    pass
                    # send msg

                    # process ...
                else:
                    pass
                    # send

                self.backstore.add(msg)
                plug.failure = None
            else:  # msg is actually an Exception
                if plugin is not None:
                    err = "plugin: {} work failed: {}".format(plugin, msg)
                    logger.error(err, exc_info=True)
                    plug.failure = msg
                    if plug.plugin_configuration["notify_on_error"]:
                        # use message text as mid to prevent multiple
                        # notifications about the same error
                        errmsg = Message(err, Priority.SILENT, mid=err, sender=self)
                        self.backstore.add(errmsg)
                else:
                    logger.warn("plugin was removed while message was in queue [{}]".format(msg.mid))


    def plugin_worker(self, queue, plugin):
        try:
            msglist = plugin.work()
            for item in msglist:
                queue.put((plugin, item))
        except Exception as e:
            queue.put((plugin, e))


    def check_messages(self):
        if not self.backstore.empty():
            for bkstr_obj in self.backstore.get_all():
                if bkstr_obj["sent_status"] == Status.unknown:
                    for plug in self.plugins:
                        if self.debug is False:
                            sent_code = plug.deliver(bkstr_obj["message"])
                            self.backstore.update(bkstr_obj["message"], status=sent_code)
                else:
                    pass
                    # check for delivery


    def check_socket(self):
        if not self.socket_queue.empty():   # TODO: "it doesn't guarantee that a
                                            #        subsequent call to put() will not block."

            buff = self.socket_queue.get()
            logger.debug("recv: [{}]".format(buff))

            if buff == SocketCommand.STATUS:
                status = ""

                for plug in self.plugins:
                    # TODO: maybe print exception?
                    fail = plug.failure

                    if fail is not None:
                        if len(str(fail)) > 60:
                            fail = str(fail)[:57] + "..."
                        else:
                            fail = str(fail)

                        fail = Termcolors.RED + str(fail) + Termcolors.RESET
                    else:
                        fail = "ok"

                    status += "{0:10s} {1:20s}: {2} {3}\n".format(plug.__class__.__name__, plug.name, self.plugin_scheduler.get_duty_cylce(plug), fail)

                if len(self.plugins) > 0:
                    status += "\n"

                status += str(self.backstore)
                self.socketManager.send(status)

                # print scheduler contents

            if buff == SocketCommand.KILL:
                try:
                    self.socketManager.send("preparing shutdown")
                except Exception as e:
                    logger.warn("sending shutdown confirmation failed")

                self.shutdown()
                sys.exit(0)

            if buff == SocketCommand.RELOAD:
                self.reload()
                self.socketManager.send("reloaded {} plugins".format(len(self.plugins)))


if __name__ == "__main__":
    params = {
        "logging_level": logging.DEBUG,
        "debug": True
    }

    mf = Mainframe(params)
    mf.backstore.add(Message("testpayload"))

    # picklefile = open("backstore.pickle", "w")
    # mf.backstore.serialize(picklefile)
    # picklefile.close()

    mf.loop()

    sys.exit(0)