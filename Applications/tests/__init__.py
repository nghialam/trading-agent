"""
Tests for __init__.py
"""

import unittest


class TestInit(unittest.TestCase):
    def test_version_exists(self):
        import src
        self.assertTrue(hasattr(src, '__version__'))
    
    def test_author_exists(self):
        import src
        self.assertTrue(hasattr(src, '__author__'))


if __name__ == '__main__':
    unittest.main()
