# License: GNU GPLv2, see LICENSE.txt
import os
import re
import shutil
import subprocess
import tempfile
import time
import pygame
from multiprocessing import Process

from .baselog import getlogger
logger = getlogger(__name__)

class LomoPlayer:

    def __init__(self, config, screen):
        """Create an instance of a video player that runs omxplayer in the
        background for video and load images using sdl.
        """
        self._vprocess = None
        self._iprocess = None
        self._temp_directory = None
        self._load_config(config)
        self._screen = screen

    def __del__(self):
        if self._temp_directory:
            shutil.rmtree(self._temp_directory)

    def _get_temp_directory(self):
        if not self._temp_directory:
            self._temp_directory = tempfile.mkdtemp()
        return self._temp_directory

    def _load_config(self, config):
        self._video_extensions = config.get('omxplayer', 'extensions') \
                                 .translate(str.maketrans('', '', ' \t\r\n.')) \
                                 .split(',')
        self._image_extensions = config.get('sdl_image', 'extensions') \
                                 .translate(str.maketrans('', '', ' \t\r\n.')) \
                                 .split(',')
        self.alpha_max = config.getint('sdl_image', 'alpha_max')
        self.alpha_min = config.getint('sdl_image', 'alpha_min')
        self.interval_sec = config.getint('sdl_image', 'interval_sec')
        self._extra_args = config.get('omxplayer', 'extra_args').split()
        self._sound = config.get('omxplayer', 'sound').lower()
        assert self._sound in ('hdmi', 'local', 'both'), 'Unknown omxplayer sound configuration value: {0} Expected hdmi, local, or both.'.format(self._sound)
        self._show_titles = config.getboolean('omxplayer', 'show_titles')
        if self._show_titles:
            title_duration = config.getint('omxplayer', 'title_duration')
            if title_duration >= 0:
                m, s = divmod(title_duration, 60)
                h, m = divmod(m, 60)
                self._subtitle_header = '00:00:00,00 --> {:d}:{:02d}:{:02d},00\n'.format(h, m, s)
            else:
                self._subtitle_header = '00:00:00,00 --> 99:59:59,00\n'
        self.background = (0, 0, 0)

    def supported_extensions(self):
        """Return list of supported file extensions."""
        return self._video_extensions + self._image_extensions

    def play(self, asset, loop=None, vol=0):
        is_media_type = lambda filename, ext: re.search('\.{0}$'.format('|'.join(ext)), filename, flags=re.IGNORECASE) is not None
        if is_media_type(asset.filename, self._image_extensions):
            self.play_image(asset, loop, vol)
        elif is_media_type(asset.filename, self._video_extensions):
            self.play_video(asset, loop, vol)
        else:
            logger.warn('not support, skip %s' % asset)

    def scaleImage(self, img, imageSize):
        (bx,by) = imageSize
        ix,iy = img.get_size()
        if ix > iy:
            scale_factor = bx/float(ix)
            sy = scale_factor * iy
            if sy > by:
                scale_factor = by/float(iy)
                sx = scale_factor * ix
                sy = by
            else:
                sx = bx
        else:
            scale_factor = by/float(iy)
            sx = scale_factor * ix
            if sx > bx:
                scale_factor = bx/float(ix)
                sx = bx
                sy = scale_factor * iy
            else:
                sy = by
    
        return pygame.transform.scale(img, (int(sx),int(sy)))

    def fade(self, image, direction):
        X, Y = self._screen.get_size()
        for i in direction:
            image.set_alpha(i)
            self._screen.fill(self.background)
            self._screen.blit(image,  ( (0.5 * X) - (0.5 * image.get_width() ), (0.5 * Y) - (0.5 * image.get_height() ) ))
            pygame.display.flip()

    def play_image(self, image, loop, vol):
        self._iprocess = Process(target=self._play_image, args=(image,))
        self._iprocess.start()

    def _play_image(self, image):
        logger.info('play image %s' % image)
        try:
            fullimg = pygame.image.load(image.filename)
            img = self.scaleImage(fullimg.convert(), self._screen.get_size())
            self.fade(img, range(self.alpha_min, self.alpha_max, 3))
            pygame.time.delay(int(self.interval_sec) * 1000)
            self.fade(img, range(self.alpha_max, self.alpha_min, -3))
        except Exception as e:
            logger.error('error loading image %s: %s' % (image, e))

    def play_video(self, movie, loop, vol):
        """Play the provided movie file, optionally looping it repeatedly."""
        logger.info('play video %s' % movie)
        self.stop(3)  # Up to 3 second delay to let the old player stop.
        # Assemble list of arguments.
        args = ['omxplayer']
        args.extend(['-o', self._sound])  # Add sound arguments.
        args.extend(self._extra_args)     # Add extra arguments from config.
        if vol is not 0:
            args.extend(['--vol', str(vol)])
        if loop is None:
            loop = movie.repeats
        if loop <= -1:
            args.append('--loop')  # Add loop parameter if necessary.
        if self._show_titles and movie.title:
            srt_path = os.path.join(self._get_temp_directory(), 'video_looper.srt')
            with open(srt_path, 'w') as f:
                f.write(self._subtitle_header)
                f.write(movie.title)
            args.extend(['--subtitles', srt_path])
        args.append(movie.filename)       # Add movie file path.
        # Run omxplayer process and direct standard output to /dev/null.
        self._vprocess = subprocess.Popen(args,
                                         stdout=open(os.devnull, 'wb'),
                                         close_fds=True)

    def is_playing(self):
        """Return true if the video/image player is running, false otherwise."""
        if self._vprocess is None:
            vplaying = False
        else:
            self._vprocess.poll()
            vplaying = self._vprocess.returncode is None

        if self._iprocess is None:
            iplaying = False
        else:
            iplaying = self._iprocess.is_alive()

        return vplaying or iplaying

    def stop(self, block_timeout_sec=0):
        """Stop the video player.  block_timeout_sec is how many seconds to
        block waiting for the player to stop before moving on.
        """
        # Stop the process if it's running.
        if self._iprocess is not None and self._iprocess.is_alive():
            self._iprocess.kill()

        if self._vprocess is not None and self._vprocess.returncode is None:
            # There are a couple processes used by omxplayer, so kill both
            # with a pkill command.
            subprocess.call(['pkill', '-9', 'omxplayer'])

        # If a blocking timeout was specified, wait up to that amount of time
        # for the process to stop.
        start = time.time()
        while self._vprocess is not None and self._vprocess.returncode is None:
            if (time.time() - start) >= block_timeout_sec:
                break
            time.sleep(0)

        # Let the process be garbage collected.
        self._vprocess = None
        self._iprocess = None

    @staticmethod
    def can_loop_count():
        return False


def create_player(config, screen):
    """Create new media player for slideshow."""
    return LomoPlayer(config, screen)

