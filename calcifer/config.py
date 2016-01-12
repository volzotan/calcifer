# Global config module, containing configuration (static)
# and setting data (dynamic, changed on runtime).

import logging

debug = False                   # sets logging level to debug and prevents that deliver() is called on plugins
logging_level = logging.INFO
backstorefile = None            # pickled backstore data
quiet = False                   # should be honored by plugins, results may differ
cork = {"enabled" : False,      # enables REST API
        "host": "localhost",
        "port": 5000,
        "SSL": True,
        "authentication": {}
        }