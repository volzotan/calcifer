from mainframe import *

from pyicloud import PyiCloudService

logger = logging.getLogger(__name__)


class Locator(Plugin):
    
    def __init__(self, config):
        self.loginname = config["login"]
        self.password = config["password"]


    def foo(self):
        self.api = PyiCloudService(self.loginname, self.password)
        print(self.api.iphone.location())