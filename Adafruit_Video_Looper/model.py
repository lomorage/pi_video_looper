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
from watchdog.observers.polling import PollingObserver
from watchdog import events

from .utils import timeit, load_image_fit_screen, is_media_type, is_short_video, get_sysinfo
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

def random_sample(iter, k):
    '''
    Reservoir sampling
    '''
    sample = []
    for n, item in enumerate(iter):
        if n < k:
            sample.append(item)
        else:
            r = random.randint(0, n)
            if r < k:
                sample[r] = item
    return sample

class WatchDogWrapIter(events.FileSystemEventHandler):

    def __init__(self, it, paths):
        self.index = 0
        self.items = list(it)
        self.added = []
        self.observer = PollingObserver()
        for path in paths:
            if os.path.exists(path):
                self.observer.schedule(self, path, recursive=True)
        self.observer.start()

    def count(self):
        return len(self.items) + len(self.added)

    def random(self):
        if self.count() != 0:
            if len(self.added) > 0:
                item = self.added.pop()
                if self.items.count(item) == 0:
                    self.items.insert(self.index, item)
                return item
            else:
                return random.choice(self.items)
        else:
            return None

    def __del__(self):
        self.observer.stop()
        self.observer.join()

    def __iter__(self):
        return self

    def __next__(self):
        if self.count() != 0:
            if len(self.added) > 0:
                item = self.added.pop()
                if self.items.count(item) == 0:
                    self.items.insert(self.index, item)
            else:
                item = self.items[self.index]

            if self.index == len(self.items) - 1:
                self.index = 0
            else:
                self.index = self.index + 1

            return item
        else:
            return None

    def on_created(self, event):
        logger.info('watchdog add %s' % event.src_path)
        asset = getMediaAsset(event.src_path)
        if not self.added.count(asset):
            self.added.append(asset)
        self._print_stats()

    def on_deleted(self, event):
        logger.info('watchdog del %s' % event.src_path)
        asset = getMediaAsset(event.src_path)
        while self.added.count(asset):
            self.added.remove(asset)
        while self.items.count(asset):
            self.items.remove(asset)
        self._print_stats()

    def _print_stats(self):
        output = 'added: %d, items: %d, total: %d' % (len(self.added), len(self.items), self.count())
        logger.info(output)

class WrapIter(object):

    def __init__(self, it):
        self.it, self.backup_it = itertools.tee(it)

    def __iter__(self):
        return self

    def __next__(self):
        asset = next(self.it, None)
        if asset is None:
            # Wrap around to the start after finishing.
            self.it, self.backup_it = itertools.tee(self.backup_it)
            asset = next(self.it, None)
        return asset

    def count(self):
        it, self.backup_it = itertools.tee(self.backup_it)
        return len(list(it))

    def random(self):
        self.it, self.backup_it = itertools.tee(self.backup_it)
        sample = random_sample(self.it, 1)
        if len(sample) > 0:
            return sample[0]
        else:
            return None

class PlaylistBase(object):

    def __init__(self, config):
        """Create a playlist from the provided list of media assets iterator."""
        self._media_type = config.get('playlist', 'media_type').upper()
        assert self._media_type in MediaType.__members__.keys(), 'Unknown media type value: {0} Expected video, image or all.'.format(self._media_type)
        self._media_type = MediaType.__members__[self._media_type]
        self._video_extensions = config.get('vlc', 'extensions') \
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

    def reload(self, func_progress=None):
        pass

    def load(self, func_progress=None):
        pass

    def _get_next(self) -> MediaAsset:
        return None

    def _get_random(self) -> MediaAsset:
        return None

    def get_next(self, is_random) -> MediaAsset:
        """Get the next asset in the playlist. Will loop to start of playlist
        after reaching end.
        """
        while True:
            if not is_random:
                asset = self._get_next()
            else:
                asset = self._get_random()

            if asset is None:
                return None
            elif self._is_media_type(asset):
                if is_media_type(asset.filename, self._video_extensions):
                    if not is_short_video(asset.filename):
                        return asset
                else:
                    return asset
            else:
                logger.info('ingore %s' % asset)

        return None

    def length(self):
        pass


class SimplePlaylist(PlaylistBase):

    def __init__(self, media_list, config):
        super().__init__(config)
        self._wrap_asset_iter = WrapIter(mediaListIter(media_list))

    def load(self, func_progress=None):
        self._length = self._wrap_asset_iter.count()

        if func_progress is not None:
            func_progress(self._length)

    def _get_next(self) -> MediaAsset:
        return next(self._wrap_asset_iter)

    def _get_random(self) -> MediaAsset:
        return self._wrap_asset_iter.random()

    def length(self):
        return self._length


class CacheFilePlayList(PlaylistBase):

    def removeCacheFile(self):
        if self.cacheFileExists():
            logger.info("remove cache file %s" % self.cache_file_path)
            os.remove(self.cache_file_path)

    def cacheFileExists(self):
        return os.path.exists(self.cache_file_path)

    def __init__(self, media_paths, extensions, config):
        super().__init__(config)
        self.cache_file_path = config.get('playlist', 'cache_path', fallback='/tmp/playlist.txt')
        self.media_paths = media_paths
        self.extensions = extensions
        if self.cacheFileExists():
            self._wrap_asset_iter = WrapIter(cacheIter(self.cache_file_path))
        else:
            self._wrap_asset_iter = WrapIter(fileSystemMediaIter(media_paths, extensions))

    def reload(self, func_progress=None):
        self.removeCacheFile()
        self._wrap_asset_iter = WrapIter(fileSystemMediaIter(self.media_paths, self.extensions))
        self._scan(func_progress)

    def load(self, func_progress=None):
        if not self.cacheFileExists():
            logger.info('%s not found, scanning %s' % (self.cache_file_path, self.media_paths))
            self._scan(func_progress)
        else:
            logger.info('loading from cache file %s' % self.cache_file_path)
            self._length = self._wrap_asset_iter.count()
            if func_progress is not None:
                func_progress(self._length)

    def _get_next(self) -> MediaAsset:
        return next(self._wrap_asset_iter)

    def _get_random(self) -> MediaAsset:
        return self._wrap_asset_iter.random()

    def length(self):
        return self._length

    @timeit
    def _scan(self, func_progress):
        self._length = 0
        try:
            tmpfile = self.cache_file_path + ".tmp"
            with open(tmpfile, 'w') as f:
                for item in self._wrap_asset_iter.it:
                    self._length += 1
                    f.write('%s\n' % item.filename)
                    if func_progress is not None:
                        func_progress(self._length)
            if self._length > 0:
                os.rename(tmpfile, self.cache_file_path)
                logger.info("scan done, create playlist file %s" % self.cache_file_path)
        except Exception as e:
            logger.error('scan error: %s' % e)


class WatchDogPlaylist(PlaylistBase):

    def __init__(self, media_paths, extensions, config):
        super().__init__(config)
        self._wrap_asset_iter = WatchDogWrapIter(fileSystemMediaIter(media_paths, extensions), media_paths)

    def load(self, func_progress=None):
        if func_progress is not None:
            func_progress(self.length())

    def _get_next(self) -> MediaAsset:
        return next(self._wrap_asset_iter)

    def _get_random(self) -> MediaAsset:
        return self._wrap_asset_iter.random()

    def length(self):
        return self._wrap_asset_iter.count()


class ResourceLoader:

    def __init__(self, playlist, config):
        self._video_extensions = config.get('vlc', 'extensions') \
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
        if len(self._cache) > 0 and self._cache[0].loading_status != LOAD_PENDING:
            asset = self._cache.pop(0)
            logger.info("pop asset %s: %s" % (asset, asset.loading_status))
            if asset in self._threads:
                t = self._threads[asset]
                if t.is_alive():
                    t.join()
                del self._threads[asset]
            asset.preload_resource = None
            asset.loading_status = LOAD_PENDING

        while len(self._cache) < self._preload:
            asset = self._playlist.get_next(is_random)
            if asset is not None and asset not in self._cache:
                self._load(asset)
                self._cache.append(asset)
            else:
                logger.warn('no new asset append: %s' % asset)
                break

        logger.info('current cache list: %s' % self._cache)

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
            logger.warn("asset not found in thread: %s" % asset)
            return LOAD_FAIL

    def _load(self, asset):
        if asset is None or asset in self._threads:
            return

        t = threading.Thread(target=self._do_load, args=(asset, ))
        self._threads[asset] = t
        t.start()

        logger.info('_load (mem: %s) %s' % (get_sysinfo(), asset.filename))

    @timeit
    def _do_load(self, asset):
        try:
            if is_media_type(asset.filename, self._image_extensions):
                asset.preload_resource = load_image_fit_screen(asset.filename)
                asset.loading_status = LOAD_SUCC
                logger.info('_do_load image %s [%s]' % (asset.filename, asset.preload_resource))
            elif is_media_type(asset.filename, self._video_extensions):
                # todo request transcoded video according to screen size
                asset.preload_resource = True
                asset.loading_status = LOAD_SUCC
                logger.info('_do_load video %s [%s]' % (asset.filename, asset.preload_resource))
            else:
                logger.warn('not support, skip %s' % asset)
                asset.loading_status = LOAD_FAIL
        except Exception as e:
            logger.error('error _do_load %s: %s' % (asset.filename, e))
            asset.loading_status = LOAD_FAIL
