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
import ShairportMetadataReader as metareader

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
        self.reader = metareader.ShairportMetadataReader()

    def control_play_pause(self):
        try:
            headers = {"Active-Remote": self.reader.get_active_remote_token()}
            url = "ctrl-int/1/playpause"
            result = self.reader._make_iTunes_request(url, None, headers)
        except Exception as err:
            logging.error("play_pause: Exception {}".format(err))
            return False
        return True

    def control_next(self):
        try:
            headers = {"Active-Remote": self.reader.get_active_remote_token()}
            url = "ctrl-int/1/nextitem"
            result = self.reader._make_iTunes_request(url, None, headers)
        except Exception as err:
            logging.error("play_pause: Exception {}".format(err))
            return False
        return True        

    def control_prev(self):
        try:
            headers = {"Active-Remote": self.reader.get_active_remote_token()}
            url = "ctrl-int/1/previtem"
            result = self.reader._make_iTunes_request(url, None, headers)
        except Exception as err:
            logging.error("play_pause: Exception {}".format(err))
            return False
        return True  

    def queue_by_persistent_id(self, persistentId):
        try:
            headers = {"Active-Remote": self.reader.get_active_remote_token()}
            # We have to build up the URL here since iTunes expects a VERY specific format about the query (can't escape single quotes or colon)
            url="ctrl-int/1/cue?command=add&query='dmap.persistentid:0x{0:X}'&mode=3".format(persistentId)
            #logging.debug("QueueSongByPersistentId headers: {} url:{}".format(headers, url))

            result = self.reader._make_iTunes_request(url, None, headers)
            if result == None:
                logging.warn("queue_by_persistent_id: Unable to queue persistentId {}.".format(persistentId))
                return False
        except Exception as err:
            logging.error("queue_by_persistent_id: Exception {}.".format(err))
            return False
        return True

    def start_itunes(self):
        logging.debug("Preparing to start iTunes.")
        try:
            process = subprocess.Popen(['ssh', self._sshConnectionName, 'osascript', '~/Documents/code/PyJukebox/AppleScript/JukeboxItunesStartup.scpt' ], stdout=subprocess.PIPE ,stderr=subprocess.PIPE) 
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
            process = subprocess.Popen(['ssh', self._sshConnectionName, 'osascript', '-l', 'JavaScript', '~/Documents/code/PyJukebox/AppleScript/GetJukeboxPlaylist.js' ], stdout=subprocess.PIPE ,stderr=subprocess.PIPE)        
            stdout, stderr = process.communicate()
            if stderr:
                self.last_error = stderr.decode("utf-8")
                logging.warning("Got Error fetching playlist. {}".format(self.last_error))
                return False
            if stdout:
                logging.debug("received json payload:" )
                utf8 = stdout.decode("utf-8")
                #logging.debug(json.dumps(utf8, indent=2))
                self._set_playlist(json.loads(utf8))
                logging.debug("fetch complete")
                self.last_error = ''
                return True
        except Exception as err:
            self.last_error = "Exception: {}".format(err)
            return False

    def _set_playlist(self, playlist):
        with self._lock:
            self._playlist = playlist

    def get_playlist(self):
        with self._lock:
            return copy.deepcopy(self._playlist)

def _testInfoAvailableCallback(itunes, key, value):
    print("Info Update: {0} = {1}".format(key, value))
    if key == 'Title':
        f.queue_by_persistent_id(0x9E73AFE715844D08)

def _testFetch():
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.DEBUG)

    f.fetch_playlist('Any Name Does not matter....Always Fetches Jukebox')

    pl = f.get_playlist()
    for k in pl:
        print("\t{} : Index: {} Title: {}".format(k, str(pl[k]['Index']), pl[k]['Name']))
    f.reader.info_available_callback = _testInfoAvailableCallback
    # Do nothing, let the metadata reader show messages
    while True:
        f.reader.loop()
        time.sleep(.250)

if __name__ == '__main__':
    f = iTunes('scott')
    _testFetch()
