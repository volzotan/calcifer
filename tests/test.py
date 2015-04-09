import unittest

from calcifer.util import *

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
        self.backstore.add(Message("testpayload", ))
        self.assertEqual('foo'.upper(), 'FOO')


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBackstore)
    unittest.TextTestRunner(verbosity=2).run(suite)