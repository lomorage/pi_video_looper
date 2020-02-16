import time
import pygame
import re

from .baselog import getlogger
logger = getlogger(__name__)

is_media_type = lambda filename, ext: re.search('\.{0}$'.format('|'.join(ext)), filename, flags=re.IGNORECASE) is not None

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        logger.info('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result
    return timed

def scale_image(img, image_size):
    (bx, by) = image_size
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

def load_image_fit_screen(imgpath):
    screen_size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
    fullimg = pygame.image.load(imgpath)
    img = scale_image(fullimg.convert(), screen_size)
    return img