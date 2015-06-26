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

    config:         configuration file path
    debug:          sets logging level to debug and prevents that deliver() is called on plugins
    logging_level:  sets logging level (overwrites debug)
    backstorefile:  pickled backstore data
    cork:           enables REST API

    """

    def load_config(self, params):
        config = Config()
        jsonconf = None

        if "config" in params:
            if isfile(params["config"]):
                try:
                    jsonconf = json.load(open(params["config"]))
                    logger.debug("config file {} loaded".format(params["config"]))
                except Exception as e:
                    logger.error("config file {} could not be parsed as valid json".format(params["config"]))
            else:
                logger.error("no config file found on given path: {}".format(params["config"]))

        if jsonconf is None:
            logger.info("no config path found, using default")
            try:
                jsonconf = json.load(open("config.json"))

                # if given option is present in configuration file,
                # overwrite default from util.Config

                if "debug" in jsonconf and jsonconf["debug"] is True:
                    config.debug = True
                    config.logging_level = logging.DEBUG

                if "logging_level" in jsonconf:
                    config.logging_level = jsonconf["logging_level"]

                if "backstorefile" in jsonconf and len(jsonconf["backstorefile"]) > 0:
                    config.backstorefile = jsonconf["backstorefile"]

                if "cork" in jsonconf and "enabled" in jsonconf["cork"] and jsonconf["cork"]["enabled"] is True:
                    config.cork["enabled"] = True

                    if "host" in jsonconf["cork"]:
                        config.cork["host"] = jsonconf["cork"]["host"]

                    if "port" in jsonconf["cork"]:
                        config.cork["port"] = int(jsonconf["cork"]["port"])

                    if "SSL" in jsonconf["cork"] and jsonconf["cork"]["SSL"] is False:
                        config.cork["SSL"] = False

                    if "authentication" in jsonconf["cork"] and len(jsonconf["cork"]["authentication"]) > 0:
                        config.cork["authentication"] = jsonconf["cork"]["authentication"]
                    else:
                        logger.warn("cork enabled but no authentication data was present")
                else:
                    logger.debug("cork was not enabled by configuration file")

                logger.debug("default config file loaded")

            except Exception as e:
                if logger.level <= logging.DEBUG:
                    logger.debug("loading default config file failed", exc_info=True)
                else:
                    logger.warn("loading default config file failed")


        if "debug" in params and params["debug"] is True:
            config.debug = True
            config.logging_level = logging.DEBUG
            logging.info("DEBUG ACTIVATED")

        if "logging_level" in params:
            config.logging_level = params["logging_level"]

        if "backstore_pickle" in params:
            config.backstorefile = params["backstore_pickle"]

        if "cork" in params and params["cork"] is True:
            config.cork["enabled"] = True
            # TODO auth data via command line

        return config


    def __init__(self, params):

        # logging needs to be initialized before the log file gets parsed
        default_logging_level = Config.logging_level

        if "logging_level" in params:
           default_logging_level = params["logging_level"]

        logging.basicConfig(level=default_logging_level,
                            format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
                            datefmt='%m-%d %H:%M')

        self.config = self.load_config(params)
        logger.setLevel(self.config.logging_level)

        self.backstore = Backstore()

        if self.config.backstorefile is not None:
            try:
                self.backstore.deserialize(self.config.backstorefile)
            except Exception as e:
                logger.warn("deserializing backstorefile {} failed".format(self.config.backstorefile), exc_info=True)

        self.plugins = []
        self.plugin_scheduler = Scheduler()

        self.message_queue = Queue()
        self.startup()

        if self.config.cork is not None and self.config.cork["enabled"] is True:
            logger.debug("initializing cork (SSL: {})".format(self.config.cork["SSL"]))
            cork.mainframe = self
            cork.users = self.config.cork["authentication"]

            # context = SSL.Context(SSL.SSLv23_METHOD)
            # context.use_privatekey_file('../cert/key.pem')
            # context.use_certificate_file('../cert/cert.pem')

            # context = ('../cert/cert.pem', '../cert/key.pem')
            context = "adhoc"

            if self.config.cork["SSL"] is True:
                from OpenSSL import SSL
                t = threading.Thread(target=cork.app.run, kwargs={"host": self.config.cork["host"], "port": self.config.cork["port"], "ssl_context": context})
            else:
                t = threading.Thread(target=cork.app.run, kwargs={"host": self.config.cork["host"], "port": self.config.cork["port"]})

            t.daemon = True
            t.start()

        self.socket_queue = Queue()
        self.socketManager = SocketManager(self.socket_queue)
        logger.debug("mainframe initialization ended")


    def __str__(self):
        return "mainframe"


    def startup(self):
        logger.info("mainframe startup")

        try:
            self.load_all_modules_from_dir(DIRECTORY, PACKAGE)
        except Exception:
            logger.warn("loading plugins failed", exc_info=True)

        # self.register_handlers()


    def reload(self):
        self.plugins = []
        self.plugin_scheduler = Scheduler()
        self.load_all_modules_from_dir(DIRECTORY, PACKAGE)


    def shutdown(self):
        logger.info("mainframe shutdown")

        for elem in self.plugins:
            elem.close()

        self.socketManager.close()


    # TODO: dir plugins is not relative to mainframe.py path (bug e.g. python calcifer/calcifer.py)
    def load_all_modules_from_dir(self, dirname, packagename):

        try:
            importlib.import_module(dirname)
        except ImportError: # if relative import fails due to exec from diff dir
            logger.debug("relative import failed")
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
                if not msg in self.backstore:
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
                        errmsg = Message(err, Priority.silent, mid=err, sender=str(self))
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
            for bkstr_obj in self.backstore.get_all_data():
                if bkstr_obj["sent_status"] == Status.unknown:
                    for plug in self.plugins:
                        if self.config.debug is False:
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

                    status += "{0:9s} {1:31s}: {2} {3}\n".format(plug.__class__.__name__, plug.name, self.plugin_scheduler.get_duty_cylce(plug), fail)

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
        "debug": True,
        "cork": True
    }

    mf = Mainframe(params)

    mf.backstore.add(Message("testpayload", mid="123"))
    mf.backstore.add(Message("testpayload2", mid="124"))

    # picklefile = open("backstore.pickle", "w")
    # mf.backstore.serialize(picklefile)
    # picklefile.close()

    mf.loop()

    sys.exit(0)