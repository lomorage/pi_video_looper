# Copyright 2015 Adafruit Industries.
# Author: Tony DiCola
# License: GNU GPLv2, see LICENSE.txt
import random
import time
import os
import re
import itertools
from typing import Optional

from .baselog import getlogger
logger = getlogger(__name__)

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        logger.info('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result
    return timed

class MediaAsset:
    """Representation of a media asset, either image or video"""

    def __init__(self, filename: str, title: Optional[str] = None, repeats: int = 1):
        """Create a playlist from the provided list of media assets."""
        self.filename = filename
        self.title = title
        self.repeats = int(repeats)
        self.playcount = 0

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

        for subdir, _, files in os.walk(mpath):
            for f in files:
                filepath = os.path.join(subdir, f)
                filename = os.path.basename(filepath)
                if filename[0] is not '.' and re.search('\.{0}$'.format(extensions), filename, flags=re.IGNORECASE):
                    #logger.debug('found %s' % filepath)
                    yield getMediaAsset(filepath)

def mediaListIter(media_list):
    for ml in media_list:
        yield ml

class Playlist:
    """Representation of a playlist of movies."""

    CACHE_FILE = '/tmp/lomo-playlist.txt'

    @classmethod
    def from_paths(cls, media_paths, extensions):
        return cls(fileSystemMediaIter(media_paths, extensions))

    @classmethod
    def from_list(cls, media_list):
        return cls(mediaListIter(media_list))

    def __init__(self, assets_iter):
        """Create a playlist from the provided list of media assets iterator."""
        self._assets_iter, self._backup_iter = itertools.tee(assets_iter)
        self._scan()

    @timeit
    def _scan(self):
        self._length = 0
        with open(self.CACHE_FILE, 'w') as f:
            for item in self._assets_iter:
                self._length += 1
                f.write('%s\n' % item.filename)

    def _get_next(self) -> MediaAsset:
        asset = next(self._assets_iter, None)
        if asset is None:
            # Wrap around to the start after finishing.
            self._assets_iter, self._backup_iter = itertools.tee(self._backup_iter)
            asset = next(self._assets_iter, None)
        return asset

    def _get_random(self) -> MediaAsset:
        # see http://metadatascience.com/2014/02/27/random-sampling-from-very-large-files/
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

    def get_next(self, is_random) -> MediaAsset:
        """Get the next asset in the playlist. Will loop to start of playlist
        after reaching end.
        """
        if not is_random:
            return self._get_next()
        else:
            return self._get_random()

    def length(self):
        """Return the number of movies in the playlist."""
        return self._length

if __name__ == '__main__':
    l = Playlist.from_paths('.', 'py')
    for i in range(l.length()):
        print(l.get_next(False).filename)

    l = Playlist.from_list([getMediaAsset('file1')])
    print(l.get_next(True))

    l = Playlist.from_list([getMediaAsset(r) for r in ['file1', 'file2']])
    print(l.get_next(True))
    print(l.get_next(True))
    print(l.get_next(True))
