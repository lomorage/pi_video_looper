import glob

class LomoReader:
    
    def __init__(self, config):
        """Create an instance of a file reader that keep track of media files in
        Lomorage mount directory
        """
        self._load_config(config)

    def _load_config(self, config):
        # mount path like "/media/WD_90C27F73C27F5C82"
        self._mount_path = config.get('lomorage', 'mount_path')

    def search_paths(self):
        """Return a list of paths to search for files. Will return a list of all
        users' home directory, like "/media/WD_90C27F73C27F5C82/jennifer/Photos/master".
        Used to generate playlist, will find all media files if no playlist files
        found in those directories,
        """
        return glob.glob(self._mount_path)

    def is_changed(self):
        """LomoReader will reload via file watchdog automatially
        """
        return False

    def idle_message(self):
        """Return a message to display when idle and no files are found."""
        return 'no media files found in %s' % self._mount_path

def create_file_reader(config, screen):
    """Create new file reader based on lomorage home directory mounted."""
    return LomoReader(config)
