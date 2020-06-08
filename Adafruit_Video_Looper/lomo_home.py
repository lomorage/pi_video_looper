import glob
import os

class LomoReader:
    
    def __init__(self, config):
        """Create an instance of a file reader that keep track of media files in
        Lomorage mount directory
        """
        self._load_config(config)
        self._enable_watchdog = False

    def _load_config(self, config):
        # mount path like "/media/WD_90C27F73C27F5C82:/media/SanDisk_ADFCEE"
        self._mount_path = config.get('lomorage', 'mount_path').split(':')
        self._mount_share_path = config.get('lomorage', 'mount_share_path')

    def search_paths(self):
        """Return a list of paths to search for files. Will return a list of all
        users' home directory, like "/media/WD_90C27F73C27F5C82/jennifer/Photos/master".
        Used to generate playlist, will find all media files if no playlist files
        found in those directories,
        """
        spaths = []

        if os.path.exists(self._mount_share_path):
            spaths.append(self._mount_share_path)
            self._enable_watchdog = True
        else:
            self._enable_watchdog = False
            for mpath in self._mount_path:
                spaths.extend(glob.glob(mpath))
        return spaths

    def is_changed(self):
        """LomoReader will reload via file watchdog automatially
        """
        return False

    def idle_message(self):
        """Return a message to display when idle and no files are found."""
        return 'No media files found, please connect hard drive first'

    def has_watchdog(self):
        return False

def create_file_reader(config, screen):
    """Create new file reader based on lomorage home directory mounted."""
    return LomoReader(config)
