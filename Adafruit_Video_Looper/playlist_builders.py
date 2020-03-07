import os
import re
import urllib.parse

from .model import Playlist, MediaAsset


def build_playlist_m3u(playlist_path: str, config):
    playlist_dirname = os.path.dirname(playlist_path)
    media_list = []

    title = None

    with open(playlist_path) as f:
        for line in f:
            if line.startswith('#'):
                if line.startswith('#EXTINF'):
                    matches = re.match(r'^#\w+:\d+(?:\s*\w+\=\".*\")*,(.*)$', line)
                    if matches:
                        title = matches[1]
            else:
                path = urllib.parse.unquote(line.rstrip())
                if not os.path.isabs(path):
                    path = os.path.join(playlist_dirname, path)
                media_list.append(MediaAsset(path, title))
                title = None

    return Playlist.from_list(media_list, config)
