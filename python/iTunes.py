#!/usr/bin/python3
import subprocess
import json
import logging
import threading
import copy
import time

import re
import urllib.parse as url_parse
import urllib.request as url_request

# Get the a playlist from iTunes

class KeyValuePair:
    def __init__(self, key, value):
        self.key = key
        self.value = value
    def __str__(self):
        return "{}: {}".format(self.key, self.value)

class iTunes:
    def __init__(self, sshConnectionName):
        self._sshConnectionName = sshConnectionName
        self._playlist = {}
        self._lock = threading.Lock()
        self.last_error = ''

        self._patternGetKeyValue = re.compile(r'(.*?)\:\s*\"?(.*)\"',re.A)
        self.InfoAvailableCallback = None
        self._storedFields = {}
        self._popen = None
        self._lock = threading.Lock()
        self._sessionId = None



########################

    def start_itunes(self):
        logging.debug("Preparing to start iTunes.")
        try:
            process = subprocess.Popen(['ssh', self._sshConnectionName, 'osascript', '~/Documents/Jukebox/JukeboxItunesStartup.scpt' ], stdout=subprocess.PIPE ,stderr=subprocess.PIPE) 
            stdout, stderr = process.communicate()
            if stderr:
                self.last_error = stderr.decode("utf-8")
                logging.warning("Error running osascript to start itunes. {}".format(self.last_error))
                return False
            if stdout:
                utf8 = stdout.decode('utf-8').strip()
                if utf8 != 'OK':
                    logging.warning("StartITunes returned non-OK result. {}".format(utf8))
                    return False
                else:
                    return True
        except Exception as err:
            self.last_error = "Exception starting iTunes. {}".format(err)
            logging.warning(err)
            return False

    def fetch_playlist(self, playlist=None):
        self._set_playlist({}) # Clear Playlist
        logging.debug("Preparing to open ssh to fetch playlist {}".format(playlist))
        try:
            process = subprocess.Popen(['ssh', self._sshConnectionName, 'osascript', '-l', 'JavaScript', '/Users/simonbs/Documents/code/PyJukebox/AppleScript/GetJukeboxPlaylist.js' ], stdout=subprocess.PIPE ,stderr=subprocess.PIPE)        
            stdout, stderr = process.communicate()
            if stderr:
                self.last_error = stderr.decode("utf-8")
                logging.warning("Got Error fetching playlist. {}".format(self.LastError))
            if stdout:
                logging.debug("received json payload:" )
                utf8 = stdout.decode("utf-8")
                #logging.debug(json.dumps(utf8, indent=2))
                self._set_playlist(json.loads(utf8))
                logging.debug("fetch complete")
                self.last_error = ''
        except Exception as err:
            self.last_error = "Exception: {}".format(err)

    def _set_playlist(self, playlist):
        with self._lock:
            self._playlist = playlist

    def get_playlist(self):
        with self._lock:
            return copy.deepcopy(self._playlist)

def _testFetch():
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.DEBUG)
    f = iTunes('scott')
    f.fetch_playlist('FirstDances')

    pl = f.get_playlist()
    for k in pl:
        print("\t{} : Index: {} Title: {}".format(k, str(pl[k]['Index']), pl[k]['Name']))

if __name__ == '__main__':
    _testFetch()
