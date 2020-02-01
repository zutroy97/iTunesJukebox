#!/usr/bin/python3
# Jukebox/iTunes Main Controller

import time
import threading
import JukeboxPanelSerialDriver as jpPanel
import iTunes
import logging

class JukeboxController:
    def __init__(self):
        self._playlist = {}
        
        self._jp = jpPanel.JukeboxPanelSerialDriver()
        self._jp.buttonPushedCallback = self._panelButtonPressedCallback
        self._instance_itunes = iTunes.iTunes('scott')

        self._setup_playlist_fetch_thread()
        self._setup_metadata_reader_thread()
        self._jp.Off()

        self._bufferJBSelection = ''

    # Creates/Starts a thread to pull events from shairport_sync
    def _setup_metadata_reader_thread(self):
        self._instance_itunes.reader.info_available_callback = self._iTunesUpdateCallback
        threading.Thread(target=self._instance_itunes.reader.loop, daemon=True).start()

    # Starts thread to fetch playlists every so often
    def _setup_playlist_fetch_thread(self):
        threading.Thread(target=self._threadPlaylistManagerLoop, daemon=True).start()

    # Every so often, fetch the jukebox playlist
    def _threadPlaylistManagerLoop(self):
        while True:
            refresh = 30 * 60
            result = self._instance_itunes.fetch_playlist()
            if result:
                #logging.debug("Playlist Fetch successful.")
                self._playlist = self._instance_itunes.get_playlist()
                self._updateDisplayForCurrentSong()
            else:
                logging.debug("Playlist Fetch failed.")
                refresh = 10
                self._playlist = {}
            logging.debug("Playlist refresh in {} seconds".format(refresh))
            time.sleep(refresh)

    def _startItunes(self):
        while True:
            result = self._instance_itunes.start_itunes()
            if result == True:
                logging.debug('iTunes successfully started.')
                break
            else:
                logging.warning("iTunesStart ERROR. {}".format(self._instance_itunes.last_error))
            time.sleep(10) # Try again

    def _updateDisplayForCurrentSong(self):
        persistentId = self._instance_itunes.reader.get_track_persistent_id()
        self._updateDisplayForSongPersistentId(persistentId)

    def _updateDisplayForSongPersistentId(self, persistentId):
        if persistentId in self._playlist:
            #logging.info("Found PersistentId in playlist!")
            self._jp.Write3(str(self._playlist[persistentId]['Index']+100))
        else:
            logging.info("Did NOT Find PersistentId {} in playlist!".format(persistentId))
            self._jp.Write3('')

    def _iTunesUpdateCallback(self, itunes, key, value):
        #logging.debug("Info Update: {0} = {1}".format(key, value))
        if key == 'Persistent ID':
            self._updateDisplayForSongPersistentId(value)
        if key == 'parser_event':
            #logging.debug("key: {} value: {}".format(key, value))
            if value == 'Pipe Open':
                #logging.debug("Got Pipe Open Event.")
                time.sleep(3)
                self._startItunes()

    def _panelButtonPressedCallback(self, buttonValue):
        #logging.debug("Got button press '{}' from jukebox keypad.". format(buttonValue))
        if buttonValue == 'P':
            return # Don't do anything with the P button for now.
        self._bufferJBSelection = self._bufferJBSelection + buttonValue
        if buttonValue == 'R':
            self._bufferJBSelection = ''
            self._jp.Led1Set(False)
        else:
            self._jp.Led1Set(True) 
        
        self._jp.Write4(self._bufferJBSelection)

        if len(self._bufferJBSelection) == 3:
            index = int(self._bufferJBSelection)
            if index == 987:
                self._instance_itunes.control_prev()
            elif index == 989:
                self._instance_itunes.control_play_pause()
            elif index == 999:
                self._instance_itunes.control_next()
            else:
                selectedIndex = index - 100
                item = [key for key in self._playlist.keys() if self._playlist[key]['Index']== selectedIndex]
                if len(item) == 1:
                    logging.debug('selecting song with persistentId: {}'.format(item[0]))
                    self._instance_itunes.queue_by_persistent_id(int(item[0], 16))
            self._bufferJBSelection = ''
            self._jp.Led1Set(False)
            self._jp.Clear4()

    def loop(self):
        i=0
        while True:
            time.sleep(.250)
            # if (i % 40) == 0:
            #     token = self._iTunesUpdateManager.GetITunesActiveRemoteToken()
            #     if token:
            #         logging.debug("Active Token is {}".format(token))
            #     else:
            #         logging.warning("No Active Token Found!")
            #     dacpId = self._iTunesUpdateManager.GetITunesDacpId()
            #     if token:
            #         logging.debug("AGetITunesDacpId is {}".format(dacpId))
            #     else:
            #         logging.warning("No GetITunesDacpId Found!")
            # i += 1


def _testPanelDriver():
    jp = jpPanel.JukeboxPanelSerialDriver()
    jp.Off()
    jp.buttonPushedCallback = _testButtonPressedCallback
    x = 0
    y = 2500    
    while True:
        jp.Write3(str(x))
        jp.Write4(str(y))

        x += 1
        if (x >= 999):
            x = 0
        y -= 1   
        if (y <= 0):
            y = 2500
        time.sleep(.1)
        
def _testButtonPressedCallback(buttonValue):
    print("Got Button Press: {0}".format(buttonValue))

def _testPlaylistFetch():
    plManager = playlist.iTunesPlaylist('scott')
    plManager.FetchPlaylistFromItunes()
    if (plManager.LastError == ''):
        pl = plManager.GetPlaylist()
        for k in pl:
            print("\t{} : Index: {} Title: {}".format(k, str(pl[k]['Index']), pl[k]['Name']))
    else:
        print("Got an error fetching the playlist. {}".format(plManager.LastError))

def start():
    controller = JukeboxController()
    mainThread = threading.Thread(target=controller.loop, daemon=False)
    mainThread.start()


if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.DEBUG)
    start()
    #_testPanelDriver()
    #_testPlaylistFetch()
    # controller = JukeboxMainController()
    # time.sleep(30)
    # pl = controller._playlist
    # for k in pl:
    #     print("\t{} : Index: {} Title: {}".format(k, str(pl[k]['Index']), pl[k]['Name']))
