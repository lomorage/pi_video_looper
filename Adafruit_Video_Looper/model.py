# Copyright 2015 Adafruit Industries.
# Author: Tony DiCola
# License: GNU GPLv2, see LICENSE.txt
import random
import os
import re
import itertools
import pygame
import threading
from typing import Optional
from enum import Enum

from .utils import timeit, load_image_fit_screen, is_media_type
from .baselog import getlogger
logger = getlogger(__name__)

random.seed()

LOAD_FAIL = -1
LOAD_PENDING = 0
LOAD_SUCC = 1

class MediaType(Enum):
    OTHERS = -1
    IMAGE = 0
    VIDEO = 1
    ALL = 2

class MediaAsset:
    """Representation of a media asset, either image or video"""

    def __init__(self, filename: str, title: Optional[str] = None, repeats: int = 1):
        """Create a playlist from the provided list of media assets."""
        self.filename = filename
        self.title = title
        self.repeats = int(repeats)
        self.playcount = 0
        self.preload_resource = None
        self.loading_status = LOAD_PENDING

    def was_played(self):
        if self.repeats > 1:
            # only count up if its necessary, to prevent memory exhaustion if player runs a long time
            self.playcount += 1
        else:
            self.playcount = 1

    def clear_playcount(self):
        self.playcount = 0

    def __lt__(self, other):
        return self.filename < other.filename

    def __eq__(self, other):
        return self.filename == other.filename

    def __hash__(self):
        return hash(self.filename)

    def __str__(self):
        return "{0} ({1})".format(self.filename, self.title) if self.title else self.filename

    def __repr__(self):
        return repr((self.filename, self.title, self.repeats))

def getMediaAsset(filepath):
    filename = os.path.basename(filepath)
    repeatsetting = re.search('_repeat_([0-9]*)x', filename, flags=re.IGNORECASE)
    if (repeatsetting is not None):
        repeat = repeatsetting.group(1)
    else:
        repeat = 1
    basename, extension = os.path.splitext(filename)
    return MediaAsset(filepath, basename, repeat)

def fileSystemMediaIter(media_paths, extensions):
    for mpath in media_paths:
        # Skip paths that don't exist or are files.
        if not os.path.exists(mpath) or not os.path.isdir(mpath):
            continue

        skipfile = os.path.join(mpath, 'SKIP')
        if os.path.exists(skipfile):
            continue

        for subdir, _, files in os.walk(mpath):
            for f in files:
                filepath = os.path.join(subdir, f)
                filename = os.path.basename(filepath)
                if filename[0] is not '.' and re.search('\.{0}$'.format(extensions), filename, flags=re.IGNORECASE):
                    logger.debug('found %s' % filepath)
                    yield getMediaAsset(filepath)

def mediaListIter(media_list):
    for ml in media_list:
        yield ml

def cacheIter(cachfile):
    try:
        with open(cachfile, 'r') as f:
            for line in f.readlines():
                yield getMediaAsset(line.rstrip())
    except Exception as e:
        logger.error('iterate %s error: %s' % (cachfile, e))

class Playlist:
    """Representation of a playlist of movies."""

    CACHE_FILE = '/opt/lomorage/var/lomo-playlist.txt'

    @staticmethod
    def cacheFileExists():
        return os.path.exists(Playlist.CACHE_FILE)

    @classmethod
    def from_paths(cls, media_paths, extensions, config):
        return cls(fileSystemMediaIter(media_paths, extensions), config)

    @classmethod
    def from_list(cls, media_list, config):
        return cls(mediaListIter(media_list), config)

    @classmethod
    def from_cache(cls, config):
        return cls(cacheIter(Playlist.CACHE_FILE), config, False)

    def __init__(self, assets_iter, config, scan=True):
        """Create a playlist from the provided list of media assets iterator."""
        self._assets_iter, self._backup_iter = itertools.tee(assets_iter)
        self._force_scan = scan
        self._media_type = config.get('playlist', 'media_type').upper()
        assert self._media_type in MediaType.__members__.keys(), 'Unknown media type value: {0} Expected video, image or all.'.format(self._media_type)
        self._media_type = MediaType.__members__[self._media_type]
        self._video_extensions = config.get('omxplayer', 'extensions') \
                                 .translate(str.maketrans('', '', ' \t\r\n.')) \
                                 .split(',')
        self._image_extensions = config.get('sdl_image', 'extensions') \
                                 .translate(str.maketrans('', '', ' \t\r\n.')) \
                                 .split(',')

    def _is_media_type(self, asset):
        if is_media_type(asset.filename, self._video_extensions):
            return self._media_type == MediaType.ALL or self._media_type == MediaType.VIDEO
        elif is_media_type(asset.filename, self._image_extensions):
            return self._media_type == MediaType.ALL or self._media_type == MediaType.IMAGE
        else:
            return False

    def load(self, func_progress=None):
        if self._force_scan:
            self._scan(func_progress)
        else:
            self._length = len(list(self._assets_iter))

        if func_progress is not None:
            func_progress(self._length)

    @timeit
    def _scan(self, func_progress):
        self._length = 0
        try:
            tmpfile = self.CACHE_FILE + ".tmp"
            with open(tmpfile, 'w') as f:
                for item in self._assets_iter:
                    self._length += 1
                    f.write('%s\n' % item.filename)
                    if func_progress is not None:
                        func_progress(self._length)
            if self._length > 0:
                os.rename(tmpfile, self.CACHE_FILE)
        except Exception as e:
            logger.error('scan error: %s' % e)

    def _get_next(self) -> MediaAsset:
        asset = next(self._assets_iter, None)
        if asset is None:
            # Wrap around to the start after finishing.
            self._assets_iter, self._backup_iter = itertools.tee(self._backup_iter)
            asset = next(self._assets_iter, None)
        return asset

    def _get_random(self) -> MediaAsset:
        # see http://metadatascience.com/2014/02/27/random-sampling-from-very-large-files/
        try:
            with open(self.CACHE_FILE, 'r') as f:
                f.seek(0, 2)
                filesize = f.tell()
                pos = random.randint(0, filesize)
                f.seek(pos)
                f.readline() # skip current line
                if f.tell() == filesize:
                    # already last line, rewind
                    f.seek(0)
                filepath = f.readline().rstrip()
                return getMediaAsset(filepath)
        except Exception as e:
            logger.error('_get_random %s error: %s' % (self.CACHE_FILE, e))

    def get_next(self, is_random) -> MediaAsset:
        """Get the next asset in the playlist. Will loop to start of playlist
        after reaching end.
        """
        i = 0
        while i < self._length:
            if not is_random:
                asset = self._get_next()
            else:
                asset = self._get_random()
            i += 1
            if self._is_media_type(asset):
                return asset

        return None

    def length(self):
        """Return the number of movies in the playlist."""
        return self._length


class ResourceLoader:

    def __init__(self, playlist, config):
        self._video_extensions = config.get('omxplayer', 'extensions') \
                                 .translate(str.maketrans('', '', ' \t\r\n.')) \
                                 .split(',')
        self._image_extensions = config.get('sdl_image', 'extensions') \
                                 .translate(str.maketrans('', '', ' \t\r\n.')) \
                                 .split(',')
        self._preload = max(config.getint('video_looper', 'preload'), 1)
        self._playlist = playlist
        self._cache = []
        self._threads= {}

    def get_next(self, is_random) -> MediaAsset:
        if len(self._cache) == self._preload:
            asset = self._cache.pop(0)
            logger.info("pop asset %s: %s" % (asset, asset.preload_resource))
            asset.preload_resource = None
            if asset in self._threads:
                t = self._threads[asset]
                if t.is_alive():
                    t.join()
                del self._threads[asset]

        while len(self._cache) < self._preload:
            asset = self._playlist.get_next(is_random)
            if asset is not None:
                self._load(asset)
                self._cache.append(asset)
            else:
                break

        if len(self._cache) > 0:
            return self._cache[0]
        else:
            return None

    def length(self):
        return self._playlist.length()

    def stop(self):
        for t in self._threads.values():
            t.join()

    def loading_status(self, asset):
        if asset in self._threads:
            return asset.loading_status
        else:
            return LOAD_FAIL

    def _load(self, asset):
        if asset is None:
            return

        t = threading.Thread(target=self._do_load, args=(asset, ))
        self._threads[asset] = t
        t.start()

        logger.info('_load %s' % asset.filename)

    @timeit
    def _do_load(self, asset):
        logger.info('_do_load %s' % asset.filename)
        try:
            if is_media_type(asset.filename, self._image_extensions):
                asset.preload_resource = load_image_fit_screen(asset.filename)
                asset.loading_status = LOAD_SUCC
            elif is_media_type(asset.filename, self._video_extensions):
                # todo request transcoded video according to screen size
                asset.preload_resource = True
                asset.loading_status = LOAD_SUCC
            else:
                logger.warn('not support, skip %s' % asset)
                asset.loading_status = LOAD_FAIL
        except Exception as e:
            logger.error('error _do_load %s: %s' % (asset.filename, e))
            asset.loading_status = LOAD_FAIL


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser().read("../assets/video_looper.ini")
    l = Playlist.from_paths('.', 'py', config)
    for i in range(l.length()):
        print(l.get_next(False).filename)

    l = Playlist.from_list([getMediaAsset('file1')], config)
    print(l.get_next(True))

    l = Playlist.from_list([getMediaAsset(r) for r in ['file1', 'file2']], config)
    print(l.get_next(True))
    print(l.get_next(True))
    print(l.get_next(True))
