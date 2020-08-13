import glob
import os
import json
import time
import urllib.request
from urllib.error import HTTPError, URLError
from socket import timeout
from .baselog import getlogger
logger = getlogger(__name__)

UPDATE_INTERVAL = 3

class LomoReader:
    
    def __init__(self, config):
        """Create an instance of a file reader that keep track of media files in
        Lomorage mount directory
        """
        self._enable_watchdog = False
        self._mount_path_exists = False
        self._mount_share_path_exists = False
        self._load_config(config)
        self._lomoframed_status = None
        self._last_update = None

    def _any_path_exists(self, paths):
        spaths = []
        for mpath in paths:
            spaths.extend(glob.glob(mpath))
        return any([os.path.exists(item) for item in spaths])

    def _load_config(self, config):
        # mount path like "/media/WD_90C27F73C27F5C82:/media/SanDisk_ADFCEE"
        self._mount_path = config.get('lomorage', 'mount_path').split(':')
        self._mount_share_path = config.get('lomorage', 'mount_share_path').split(':')
        self._mount_path_exists = self._any_path_exists(self._mount_path)
        self._mount_share_path_exists = self._any_path_exists(self._mount_share_path)
        logger.info("loading mount_path: %s [%s], mount_share_path: %s [%s]" %
            (self._mount_path, self._mount_path_exists, self._mount_share_path, self._mount_share_path_exists))

    def search_paths(self):
        """Return a list of paths to search for files. Will return a list of all
        users' home directory, like "/media/WD_90C27F73C27F5C82/jennifer/Photos/master".
        Used to generate playlist, will find all media files if no playlist files
        found in those directories,
        """
        spaths = []

        if self._any_path_exists(self._mount_share_path):
            self._enable_watchdog = True
            for mpath in self._mount_share_path:
                spaths.extend(glob.glob(mpath))
        else:
            self._enable_watchdog = False
            for mpath in self._mount_path:
                spaths.extend(glob.glob(mpath))
        logger.info('search path: %s' % spaths)
        return spaths

    def is_changed(self):
        """Check if any changes on existence of mount path and mount share path,
        will prefer media share path over media path
        """
        #print('old mount_path_exists: %s, mount_share_path_exists: %s' % (self._mount_path_exists, self._mount_share_path_exists))
        mount_path_exists = self._any_path_exists(self._mount_path)
        mount_share_path_exists = self._any_path_exists(self._mount_share_path)
        #print('new mount_path_exists: %s, mount_share_path_exists: %s' % (mount_path_exists, mount_share_path_exists))

        changed = False

        # if share path changes, we need reload
        if mount_share_path_exists != self._mount_share_path_exists:
            changed = True
            logger.info('lomo search path changed to %s' % self._mount_share_path)

        # if home path found, if we have share path, ignore, otherwise need reload
        if mount_path_exists != self._mount_path_exists and not mount_share_path_exists:
            changed = True
            logger.info('lomo search path changed to %s' % self._mount_path)

        self._mount_path_exists = mount_path_exists
        self._mount_share_path_exists = mount_share_path_exists
        return changed

    def get_lomoframed_status(self):
        now = time.time()
        if self._last_update is None:
            self._last_update = now

        if self._lomoframed_status is not None and (now - self._last_update < UPDATE_INTERVAL):
            return self._lomoframed_status

        self._last_update = now

        sysstatus = -1
        mountstatus = -1
        keepalivestatus = -1
        try:
            url = 'http://127.0.0.1:8003/system'
            response = urllib.request.urlopen(url, timeout=3)
            resp = json.loads(response.read())
            sysstatus = resp['SystemStatus']
            mountstatus = resp['MountStatus']
            keepalivestatus = resp['KeepaliveStatus']
            #logger.debug('get_lomoframed_status: %d' % resp)
        except (HTTPError, URLError) as error:
            logger.error('get_lomoframed_status: %s, %s' %(error, url))
        except timeout:
            logger.error('get_lomoframed_status: %s socket timed out' % url)
        except Exception as RESTex:
            logger.error('get_lomoframed_status: %s, %s' %(RESTex, url))
        return (sysstatus, mountstatus, keepalivestatus)

    def idle_message(self):
        """Return a message to display when idle and no files are found."""
        sysstatus, mountstatus, keepalivestatus = self.get_lomoframed_status()
        message = ''
        if sysstatus == -1:
            message = 'System Error, please contact support@lomorage.com'
        elif sysstatus == 0 or sysstatus == 1:
            message = 'Scan the QRCode with Lomorage APP to bind LomoFrame'
        elif sysstatus == 2:
            message = 'Can\'t reach server, please check network connectivity'
        elif sysstatus == 3:
            # 1. show login error info
            # 2. let user scan qrcode (ip:port) to reset/unbind
            message = 'Login Lomod failure, you can unregister by scanning the QRCode'
        elif sysstatus == 4:
            if mountstatus == 0 and keepalivestatus == 0:
                message = 'LomoFrame bind successfully, you can share Photo with Lomorage APP'
            elif mountstatus == -1:
                message = 'Mount failure, please check network connectivity'
            elif keepalivestatus == -1:
                message = 'Keepalive failure, please check network connectivity'
            else:
                message = 'Connecting server...'

        if sysstatus == 0 and self._lomoframed_status is not None and self._lomoframed_status[0] != 0:
            # restart if changed to uninit
            logger.info('need reload')
            message = 'reloading...'

        self._lomoframed_status = (sysstatus, mountstatus, keepalivestatus)
        return message

    def enable_watchdog(self):
        return self._enable_watchdog

def create_file_reader(config, screen):
    """Create new file reader based on lomorage home directory mounted."""
    return LomoReader(config)
