import unittest

import util
from mainframe import *
from plugins.dummy import Dummy

class Skeleton(object):
    pass

class TestMessage(unittest.TestCase):

    def setUp(self):
        self.testmessage = Message("testmessage")

        self.sender = Dummy({})
        self.sender.name = "dummytestname"

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

    def test_JSONencoding(self):
        msg = Message("testpayload", mid="test", sender=self.sender)

        print json.dumps(msg, cls=util.MessageJSONEncoder)

    def test_JSONdecoding(self):
        testmessages = []
        encodedmessages = []
        decodedmessages = []

        testmessages.append(Message("message1"))
        testmessages.append(Message("message2", mid="123"))
        testmessages.append(Message("message3", mid="123", priority=Priority.medium))
        testmessages.append(Message("message4", mid="123", priority=Priority.medium, sender=self.sender))

        for msg in testmessages:
            tmp = json.dumps(msg, cls=util.MessageJSONEncoder)

            encodedmessages.append(tmp)
            decodedmessages.append(MessageJSONDecoder().decode(tmp))

        for i in range(0, len(decodedmessages)):
            self.assertEqual(decodedmessages[i], encodedmessages[i])


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

        self.backstore.clear()

        self.backstore.add(msg1)
        self.backstore.add(msg2)

        self.assertEqual(len(self.backstore.get_all_messages()), 2)
        self.assertEqual(self.backstore.get(msg1.mid), msg1)

    def test_serialize(self):
        picklefile = open("backstore.pickle", "w")
        self.backstore.serialize(picklefile)

        self.backstore.clear()

        self.assertEqual(self.backstore.empty(), True)

        picklefile = open("backstore.pickle", "r")
        self.backstore.deserialize(picklefile)

        self.assertEqual(self.backstore.get(self.testmessage.mid), self.testmessage)

    def test_deserialize(self):
        pass

    def test_contains(self):
        testmsg = Message("testpayload")

        if testmsg in self.backstore:
            self.assertTrue(False)
        else:
            self.assertTrue(True)

        if self.testmessage in self.backstore:
            self.assertTrue(True)
        else:
            self.assertTrue(False)



    def test_cleanup(self):
        add_time = datetime.datetime.now()
        add_time = add_time - datetime.timedelta(minutes=util.CLEANUP_TIME + 1)

        self.backstore.data = {
            "examplemid": { "message": self.testmessage,
                            "add_time": add_time,
                            "update_time": None,
                            "sent_status": Status.unknown
                            }
        }

        self.assertEqual(len(self.backstore.get_all_messages()), 1)
        self.assertEqual(self.backstore.cleanup(), 1)
        self.assertEqual(self.backstore.empty(), True)


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


class TestRestInterface(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass