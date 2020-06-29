import glob
import os
from .baselog import getlogger
logger = getlogger(__name__)

class LomoReader:
    
    def __init__(self, config):
        """Create an instance of a file reader that keep track of media files in
        Lomorage mount directory
        """
        self._load_config(config)
        self._enable_watchdog = False

    def _any_path_exists(self, paths):
        return any([os.path.exists(item) for item in paths])

    def _load_config(self, config):
        # mount path like "/media/WD_90C27F73C27F5C82:/media/SanDisk_ADFCEE"
        self._mount_path = config.get('lomorage', 'mount_path').split(':')
        self._mount_share_path = config.get('lomorage', 'mount_share_path').split(':')
        logger.info("loading mount_path: %s, mount_share_path: %s" % (self._mount_path, self._mount_share_path))
        self._mount_path_exists = self._any_path_exists(self._mount_path)
        self._mount_share_path_exists = self._any_path_exists(self._mount_share_path)

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
        return spaths

    def is_changed(self):
        """Check if any changes on existence of mount path and mount share path,
        will prefer media share path over media path, that is:
        1. if we have share path, then use it, don't care whether media path exists or not
        2. if we don't have share path, if media path changed, we need update playlist
        3. if we have share path changed, we should update playlist anyway
        """
        #print('old mount_path_exists: %s, mount_share_path_exists: %s' % (self._mount_path_exists, self._mount_share_path_exists))
        mount_path_exists = self._any_path_exists(self._mount_path)
        mount_share_path_exists = self._any_path_exists(self._mount_share_path)
        #print('new mount_path_exists: %s, mount_share_path_exists: %s' % (mount_path_exists, mount_share_path_exists))

        changed = False
        if mount_share_path_exists != self._mount_share_path_exists:
            changed = True

        if mount_path_exists != self._mount_path_exists and not mount_share_path_exists:
            changed = True

        self._mount_path_exists = mount_share_path_exists
        self._mount_share_path_exists = mount_share_path_exists
        return changed

    def idle_message(self):
        """Return a message to display when idle and no files are found."""
        return 'No media files found, please connect hard drive first'

    def enable_watchdog(self):
        return self._enable_watchdog

def create_file_reader(config, screen):
    """Create new file reader based on lomorage home directory mounted."""
    return LomoReader(config)
