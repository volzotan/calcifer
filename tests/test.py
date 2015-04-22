import unittest

from calcifer.util import *
from calcifer.mainframe import *

from calcifer import calcifer

class Skeleton(object):
    pass

class TestMessage(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_message_identity(self):
        msg1 = Message("testpayload", mid="test", sender=self)
        msg2 = Message("testpayload", mid="test", sender=self)

        self.assertEqual(msg1, msg2)

    def test_random_mid(self):
        msg1 = Message("testpayload")
        msg2 = Message("testpayload")

        self.assertNotEqual(msg1.mid, msg2.mid)

class TestBackstore(unittest.TestCase):

    def setUp(self):
        self.backstore = Backstore()
        self.testmessage = Message("testmessage")
        self.backstore.add(self.testmessage)

    def tearDown(self):
        pass

    def test_add(self):
        msg1 = Message("testpayload1")
        msg2 = Message("testpayload2")

        self.backstore.add(msg1)
        self.backstore.add(msg2)

        self.assertEqual(len(self.backstore.get_all()), 2)
        self.assertEqual(self.backstore.get(msg1), msg1)

    def test_serialize(self):
        picklefile = open("backstore.pickle", "w")
        self.backstore.serialize(picklefile)

        self.backstore.clear()

        self.assertEqual(self.backstore.empty(), True)

        #picklefile.close()
        picklefile = open("backstore.pickle", "r")
        self.backstore.deserialize(picklefile)

        self.assertEqual(self.backstore.get(self.testmessage), self.testmessage)

    def test_deserialize(self):
        pass

    def test_cleanup(self):
        pass


class TestMainframe(unittest.TestCase):

    def setUp(self):
        __package__ == "calcifer"

    def tearDown(self):
        self.mainframe.shutdown()

    def test_params(self):
        params = {
            "debug": True,
            "logging_level": logging.WARN
        }

        self.mainframe = Mainframe(params)

        self.assertEqual(self.mainframe.debug, True)
        self.assertEqual(self.mainframe.logging_level, logging.WARN)
        # self.assertEqual(self.mainframe.logger,)

# class TestSocketCommunication(unittest.TestCase):
#
#     def setUp(self):
#         pass
#
#     def tearDown(self):
#         self.stop()
#
#     def test_start(self):
#         self.calc = calcifer
#         skeleton = Skeleton()
#         setattr(skeleton, "debug", True)
#         setattr(skeleton, "no_detach", False)
#         self.calc.args = skeleton
#         self.calc.start()


class TestPlugins(unittest.TestCase):

    def setUp(self):
        pass

    #test initialization of every plugin with every conf in ../calcifer/plugins
