import pkgutil
import importlib
import sys
import time

from os import listdir
from os.path import isfile, join

import json
import logging

from util import *

from Queue import Queue
from socketManager import SocketManager

logger = logging.getLogger(__name__)

DIRECTORY = "plugins"
SLEEP_DURATION = 1  # in sec
LOGGING_LEVEL = logging.DEBUG

class Mainframe(object):

    def __init__(self):
        logging.basicConfig(level=LOGGING_LEVEL,
                            format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
                            datefmt='%m-%d %H:%M'
                            )

        self.backstore = Backstore()
        self.plugins = []
        self.plugin_scheduler = Scheduler()

        self.startup()

        self.queue = Queue()
        self.socketManager = SocketManager(self.queue)


    def startup(self):
        logger.info("Mainframe Startup")

        self.load_all_modules_from_dir(DIRECTORY)
        # self.register_handlers()


    def reload(self):
        self.plugins = []
        self.plugin_scheduler = Scheduler()
        self.load_all_modules_from_dir(DIRECTORY)


    def shutdown(self):
        logger.info("Mainframe Shutdown")

        for elem in self.plugins:
            elem.close()

        self.socketManager.close()


    def load_all_modules_from_dir(self, dirname):
        importlib.import_module(dirname)
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
                        if plug.plugin_configuration["notify_on_error"]:
                            pass
                            # TODO: create message


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
                try:
                    msglist = plug.work()

                    for msg in msglist:
                        if not self.backstore.contains(msg):
                            pass
                            # send msg

                            # process ...
                        else:
                            pass
                            # send

                        self.backstore.add(msg)

                except Exception as e:
                    err = "plugin: {} work failed: {}".format(plug, e)
                    logger.error(err, exc_info=True)
                    if plug.plugin_configuration["notify_on_error"]:
                        # use message text as mid to prevent multiple
                        # notifications about the same error
                        msg = Message(err, Priority.SILENT, mid=err)
                        self.backstore.add(msg)

                # do sth with all these messages ...


    def check_messages(self):
        if not self.backstore.empty():
            for bkstr_obj in self.backstore.get_all():
                if bkstr_obj["sent_status"] == Status.UNKNOWN:
                    for plug in self.plugins:
                        sent_code = plug.deliver(bkstr_obj["message"])
                        self.backstore.update(bkstr_obj["message"], status=sent_code)
                else:
                    pass
                    # check for delivery


    def check_socket(self):
        if not self.queue.empty():  # TODO: "it doesn't guarantee that a
                                    #        subsequent call to put() will not block."

            buff = self.queue.get()
            logger.debug("recv: [{}]".format(buff))

            if buff == SocketCommand.STATUS:
                self.socketManager.send(str(self.backstore))

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
    Mainframe().loop()
    sys.exit(0)