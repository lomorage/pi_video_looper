import unittest
import configparser
from Adafruit_Video_Looper.model import *
from watchdog import events
from shutil import copyfile

class TestSimplePlaylist(unittest.TestCase):

    def setUp(self):
        config = configparser.ConfigParser()
        config.read("test/video_looper.ini")
        self.file_list = ['file1.png', 'file2.jpg', 'file4']
        self.playlist = SimplePlaylist([getMediaAsset(r) for r in self.file_list], config)
        self.playlist.load()

    def test_next_random(self):
        self.assertEqual(self.playlist.length(), 3)
        self.assertIsNotNone(self.playlist.get_next(True))
        self.assertIsNotNone(self.playlist.get_next(True))
        self.assertIsNotNone(self.playlist.get_next(True))

    def test_next(self):
        self.assertEqual(self.playlist.length(), 3)
        self.assertEqual(self.playlist.get_next(False).filename, self.file_list[0])
        self.assertEqual(self.playlist.get_next(False).filename, self.file_list[1])
        self.assertEqual(self.playlist.get_next(False).filename, self.file_list[0])

    def test_empty_playlist(self):
        config = configparser.ConfigParser()
        config.read("test/video_looper.ini")
        playlist = SimplePlaylist([], config)
        playlist.load()
        self.assertEqual(playlist.length(), 0)
        self.assertIsNone(playlist.get_next(True))
        self.assertIsNone(playlist.get_next(False))

class TestCacheFilePlayList(unittest.TestCase):

    def setUp(self):
        config = configparser.ConfigParser()
        config.read("test/video_looper.ini")
        self.playlist = CacheFilePlayList(['test/media/home'], '*.png', config)
        self.playlist.removeCacheFile()
        self.playlist.load()
        self.another_file = 'test/media/home/IMG_6849.bak.png'

    def tearDown(self):
        self.playlist.removeCacheFile()
        if os.path.exists(self.another_file):
            os.remove(self.another_file)

    def test_next(self):
        asset_name_lst = ['test/media/home/20190601_12440.png', 'test/media/home/IMG_6849.png']
        self.assertTrue(self.playlist.cacheFileExists())
        self.assertEqual(self.playlist.length(), 2)
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[0])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[1])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[0])

    def test_next_random(self):
        self.assertTrue(self.playlist.cacheFileExists())
        self.assertEqual(self.playlist.length(), 2)
        self.assertIsNotNone(self.playlist.get_next(True))
        self.assertIsNotNone(self.playlist.get_next(True))
        self.assertIsNotNone(self.playlist.get_next(True))

    def test_reload(self):
        copyfile('test/media/home/IMG_6849.png', self.another_file)
        asset_name_lst = ['test/media/home/20190601_12440.png', self.another_file, 'test/media/home/IMG_6849.png']
        self.playlist.reload()
        self.assertTrue(self.playlist.cacheFileExists())
        self.assertEqual(self.playlist.length(), 3)
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[0])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[1])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[2])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[0])
        os.remove(self.another_file)

    def test_empty_playlist(self):
        self.playlist.removeCacheFile()
        config = configparser.ConfigParser()
        config.read("test/video_looper.ini")
        playlist = CacheFilePlayList(['noexist'], '*.png', config)
        playlist.load()
        self.assertEqual(playlist.length(), 0)
        self.assertIsNone(playlist.get_next(True))
        self.assertIsNone(playlist.get_next(False))

class TestWatchDogPlaylist(unittest.TestCase):

    def setUp(self):
        config = configparser.ConfigParser()
        config.read("test/video_looper.ini")
        self.playlist = WatchDogPlaylist(['test/media'], '*.png', config)
        self.playlist.load()

    def test_next(self):
        asset_name_lst = ['test/media/home/20190601_12440.png', 'test/media/home/IMG_6849.png']
        self.assertEqual(self.playlist.length(), 2)
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[0])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[1])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[0])

    def test_next_random(self):
        self.assertEqual(self.playlist.length(), 2)
        self.assertIsNotNone(self.playlist.get_next(True))
        self.assertIsNotNone(self.playlist.get_next(True))
        self.assertIsNotNone(self.playlist.get_next(True))

    def test_add(self):
        asset_name_lst = ['test/media/home/20190601_12440.png', 'test/media/home/IMG_6849.png']
        e = events.FileCreatedEvent('added.jpg')
        self.playlist._wrap_asset_iter.on_created(e)
        asset_name_lst.insert(0, 'added.jpg')
        self.assertEqual(self.playlist.length(), 3)
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[0])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[1])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[2])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[0])

    def test_remove(self):
        asset_name_lst = ['test/media/home/20190601_12440.png', 'test/media/home/IMG_6849.png']
        e = events.FileDeletedEvent('test/media/home/20190601_12440.png')
        self.playlist._wrap_asset_iter.on_deleted(e)
        self.assertEqual(self.playlist.length(), 1)
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[1])
        self.assertEqual(self.playlist.get_next(False).filename, asset_name_lst[1])

    def test_empty_playlist(self):
        config = configparser.ConfigParser()
        config.read("test/video_looper.ini")
        playlist = WatchDogPlaylist(['noexist'], '*.png', config)
        playlist.load()
        self.assertEqual(playlist.length(), 0)
        self.assertIsNone(playlist.get_next(True))
        self.assertIsNone(playlist.get_next(False))

if __name__ == '__main__':
    unittest.main()
