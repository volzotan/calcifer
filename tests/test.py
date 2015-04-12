import unittest

from calcifer.util import *
from calcifer.mainframe import *

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

        self.assertNotEqual(msg1, msg2)

class TestBackstore(unittest.TestCase):

    def setUp(self):
        self.backstore = Backstore()

    def tearDown(self):
        pass

    def test_add(self):
        msg1 = Message("testpayload1")
        msg2 = Message("testpayload2")

        self.backstore.add(msg1)
        self.backstore.add(msg2)

        self.assertEqual(len(self.backstore.get_all()), 2)
        self.assertEqual(self.backstore.get(msg1), msg1)

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

class TestSocketCommunication(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testStart(self):
        calcifer.start()


class TestPlugins(unittest.TestCase):

    def setUp(self):
        pass

    #test every plugin with every conf in ../calcifer/plugins



# if __name__ == '__main__':
#     suite = unittest.TestLoader().loadTestsFromTestCase(TestBackstore)
#     unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    unittest.main()