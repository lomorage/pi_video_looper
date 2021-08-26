# License: GNU GPLv2, see LICENSE.txt
import os
import re
import shutil
import subprocess
import tempfile
import time
import pygame
from multiprocessing import Process

from .alsa_config import parse_hw_device
from .utils import timeit, load_image_fit_screen, is_media_type
from .baselog import getlogger
logger = getlogger(__name__)

class LomoPlayer:

    def __init__(self, config, screen):
        """Create an instance of a video player that runs vlc in the
        background for video and load images using sdl.
        """
        self._vprocess = None
        self._iprocess = None
        self._temp_directory = None
        self._screen = screen
        self._load_config(config)

    def __del__(self):
        if self._temp_directory:
            shutil.rmtree(self._temp_directory)

    def _get_temp_directory(self):
        if not self._temp_directory:
            self._temp_directory = tempfile.mkdtemp()
        return self._temp_directory

    def _load_config(self, config):
        self._video_extensions = config.get('vlc', 'extensions') \
                                 .translate(str.maketrans('', '', ' \t\r\n.')) \
                                 .split(',')
        self._image_extensions = config.get('sdl_image', 'extensions') \
                                 .translate(str.maketrans('', '', ' \t\r\n.')) \
                                 .split(',')
        self._alpha_max = config.getint('sdl_image', 'alpha_max')
        self._alpha_min = config.getint('sdl_image', 'alpha_min')
        self._interval_sec = config.getint('sdl_image', 'interval_sec')
        self._bgcolor = list(map(int, config.get('video_looper', 'bgcolor')
                                             .translate(str.maketrans('','', ','))
                                             .split()))
        self._preload = (config.getint('video_looper', 'preload') > 0)
        self._extra_args = config.get('vlc', 'extra_args').split()
        self._sound = config.get('vlc', 'sound').lower()
        #assert self._sound in ('hdmi', 'local', 'both', 'alsa'), 'Unknown sound configuration value: {0} Expected hdmi, local, both or alsa.'.format(self._sound)
        #self._alsa_hw_device = parse_hw_device(config.get('alsa', 'hw_device'))
        #if self._alsa_hw_device != None and self._sound == 'alsa':
        #    self._sound = 'alsa:hw:{},{}'.format(self._alsa_hw_device[0], self._alsa_hw_device[1])

        self._show_titles = config.getboolean('vlc', 'show_titles')
        if self._show_titles:
            title_duration = config.getint('vlc', 'title_duration')
            if title_duration >= 0:
                m, s = divmod(title_duration, 60)
                h, m = divmod(m, 60)
                self._subtitle_header = '00:00:00,00 --> {:d}:{:02d}:{:02d},00\n'.format(h, m, s)
            else:
                self._subtitle_header = '00:00:00,00 --> 99:59:59,00\n'

    def supported_extensions(self):
        """Return list of supported file extensions."""
        return self._video_extensions + self._image_extensions

    def play(self, asset, loop=None, vol=0):
        if is_media_type(asset.filename, self._image_extensions):
            self.play_image(asset, loop, vol)
        elif is_media_type(asset.filename, self._video_extensions):
            self.play_video(asset, loop, vol)
        else:
            logger.warn('not support, skip %s' % asset)

    def fade(self, image, direction):
        X, Y = self._screen.get_size()
        for i in direction:
            image.set_alpha(i)
            self._screen.fill(self._bgcolor)
            self._screen.blit(image,  ( (0.5 * X) - (0.5 * image.get_width() ), (0.5 * Y) - (0.5 * image.get_height() ) ))
            pygame.display.flip()

    def play_image(self, image, loop, vol):
        self._iprocess = Process(target=self._play_image, args=(image,))
        self._iprocess.start()

    def _play_image(self, image):
        logger.info('play image %s' % image)
        try:
            if self._preload:
                img = image.preload_resource
            else:
                img = load_image_fit_screen(image.filename)

            self.fade(img, range(self._alpha_min, self._alpha_max, 3))
            pygame.time.delay(int(self._interval_sec) * 1000)
            self.fade(img, range(self._alpha_max, self._alpha_min, -3))
        except Exception as e:
            logger.error('error loading image %s: %s' % (image, e))

    def play_video(self, movie, loop, vol):
        """Play the provided movie file, optionally looping it repeatedly."""
        logger.info('play video %s' % movie)
        self._screen.fill(self._bgcolor)
        pygame.display.flip()
        self.stop(3)  # Up to 3 second delay to let the old player stop.
        # Assemble list of arguments.
        args = ['cvlc', '--play-and-exit']
        #args.extend(['--alsa-audio-device', self._sound])  # Add sound arguments.
        #args.extend(self._extra_args)     # Add extra arguments from config.
        if vol is not 0:
            args.extend(['--gain', str(vol)])
        if loop is None:
            loop = movie.repeats
        if loop <= -1:
            args.append('--loop')  # Add loop parameter if necessary.
        if self._show_titles and movie.title:
            srt_path = os.path.join(self._get_temp_directory(), 'video_looper.srt')
            with open(srt_path, 'w') as f:
                f.write(self._subtitle_header)
                f.write(movie.title)
            args.extend(['--sub-file', srt_path])
        args.append(movie.filename)       # Add movie file path.
        # Run vlc process and direct standard output to /dev/null.
        logger.info('play video: %s' % args)
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
            # There are a couple processes used by vlc, so kill both
            # with a pkill command.
            subprocess.call(['pkill', '-9', 'vlc'])

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

