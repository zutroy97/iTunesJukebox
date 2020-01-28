#!/usr/bin/python3
import subprocess
import json
import logging
import threading
import copy
import time

# Get the a playlist from iTunes

class iTunesPlaylist:
    def __init__(self, sshConnectionName):
        self._sshConnectionName = sshConnectionName
        self._playlist = {}
        self._lock = threading.Lock()
        self.LastError = ''

    def StartITunes(self):
        logging.debug("Preparing to start iTunes.")
        try:
            process = subprocess.Popen(['ssh', self._sshConnectionName, 'osascript', '~/Documents/Jukebox/JukeboxItunesStartup.scpt' ], stdout=subprocess.PIPE ,stderr=subprocess.PIPE) 
            stdout, stderr = process.communicate()
            if stderr:
                self.LastError = stderr.decode("utf-8")
                logging.warning("Error running osascript to start itunes. {}".format(self.LastError))
                return False
            if stdout:
                utf8 = stdout.decode('utf-8').strip()
                if utf8 != 'OK':
                    logging.warning("StartITunes returned non-OK result. {}".format(utf8))
                    return False
                else:
                    return True
        except Exception as err:
            self.LastError = "Exception starting iTunes. {}".format(err)
            logging.warning(err)
            return False

    def FetchPlaylistFromItunes(self, playlist=None):
        self._setPlaylist({}) # Clear Playlist
        logging.debug("Preparing to open ssh to fetch playlist {}".format(playlist))
        try:
            process = subprocess.Popen(['ssh', self._sshConnectionName, 'osascript', '-l', 'JavaScript', '/Users/simonbs/Documents/code/PyJukebox/AppleScript/GetJukeboxPlaylist.js' ], stdout=subprocess.PIPE ,stderr=subprocess.PIPE)        
            stdout, stderr = process.communicate()
            if stderr:
                self.LastError = stderr.decode("utf-8")
                logging.warning("Got Error fetching playlist. {}".format(self.LastError))
            if stdout:
                logging.debug("received json payload:" )
                utf8 = stdout.decode("utf-8")
                #logging.debug(json.dumps(utf8, indent=2))
                self._setPlaylist(json.loads(utf8))
                logging.debug("fetch complete")
                self.LastError = ''
        except Exception as err:
            self.LastError = "Exception: {}".format(err)

    def _setPlaylist(self, playlist):
        with self._lock:
            self._playlist = playlist

    def GetPlaylist(self):
        with self._lock:
            return copy.deepcopy(self._playlist)

def _testFetch():
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.DEBUG)
    f = iTunesPlaylist('scott')
    f.FetchPlaylistFromItunes('FirstDances')

    pl = f.GetPlaylist()
    for k in pl:
        print("\t{} : Index: {} Title: {}".format(k, str(pl[k]['Index']), pl[k]['Name']))

if __name__ == '__main__':
    _testFetch()
