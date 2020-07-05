import unittest
import configparser
import os
from Adafruit_Video_Looper.lomo_home import *

class TestLomoHomeReader(unittest.TestCase):

    def setUp(self):
        self.share_dir = 'test/media/share'
        if os.path.exists(self.share_dir):
            os.rmdir(self.share_dir)
        config = configparser.ConfigParser()
        config.read("test/video_looper.ini")
        self.reader = create_file_reader(config, None)

    def test_search_paths_home_glob(self):
        config = configparser.ConfigParser()
        config.read("test/video_looper.ini")
        config['lomorage']['mount_path'] = 'test/media/ho*'
        self.reader = create_file_reader(config, None)
        searchPaths = self.reader.search_paths()
        self.assertEqual(len(searchPaths), 1)
        self.assertEqual(searchPaths[0], 'test/media/home')
        self.assertFalse(self.reader.enable_watchdog())

    def test_search_paths_home(self):
        searchPaths = self.reader.search_paths()
        self.assertEqual(len(searchPaths), 1)
        self.assertEqual(searchPaths[0], 'test/media/home')
        self.assertFalse(self.reader.enable_watchdog())
        self.assertFalse(self.reader.is_changed())
        self.assertFalse(self.reader.is_changed())

    def test_search_paths_share(self):
        os.mkdir(self.share_dir)
        self.assertTrue(self.reader.is_changed())
        self.assertFalse(self.reader.is_changed())
        searchPaths = self.reader.search_paths()
        self.assertEqual(len(searchPaths), 1)
        self.assertEqual(searchPaths[0], self.share_dir)
        self.assertTrue(self.reader.enable_watchdog())
        os.rmdir(self.share_dir)

    def test_search_paths_changes(self):
        self.assertFalse(self.reader.is_changed())
        self.assertFalse(self.reader.is_changed())
        searchPaths = self.reader.search_paths()
        self.assertEqual(searchPaths[0], 'test/media/home')
        self.assertFalse(self.reader.enable_watchdog())

        os.mkdir(self.share_dir)
        self.assertTrue(self.reader.is_changed())
        self.assertFalse(self.reader.is_changed())
        searchPaths = self.reader.search_paths()
        self.assertEqual(searchPaths[0], self.share_dir)
        self.assertTrue(self.reader.enable_watchdog())

        os.rmdir(self.share_dir)
        self.assertTrue(self.reader.is_changed())
        self.assertFalse(self.reader.is_changed())
        searchPaths = self.reader.search_paths()
        self.assertEqual(searchPaths[0], 'test/media/home')
        self.assertFalse(self.reader.enable_watchdog())