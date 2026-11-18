import unittest
from app import response_for

class AppTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(response_for("/health"), (200, {"status": "ok"}))
    def test_home(self):
        code, body = response_for("/")
        self.assertEqual(code, 200)
        self.assertEqual(body["service"], "practice7")
        self.assertIn("commit", body)
    def test_unknown(self):
        self.assertEqual(response_for("/missing")[0], 404)
