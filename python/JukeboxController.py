#!/usr/bin/python3
# Jukebox/iTunes Main Controller

import time
import threading
import JukeboxPanelSerialDriver as jpPanel
import iTunes
import logging
import socket

class JukeboxController:
    def __init__(self):
        self._playlist = {}
        
        self._jp = jpPanel.JukeboxPanelSerialDriver()
        self._jp.buttonPushedCallback = self._panelButtonPressedCallback
        self._instance_itunes = iTunes.iTunes('scott') #TODO: Make configurable

        self._setup_playlist_fetch_thread()
        self._setup_metadata_reader_thread()
        self._jp.Off()

        self._bufferJBSelection = ''
        self._showIpAddress()
        self._isShowingIpAddress = False

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
            refresh = 30 * 60 # TODO: Make configurable
            result = self._instance_itunes.fetch_playlist()
            if result:
                #logging.debug("Playlist Fetch successful.")
                self._playlist = self._instance_itunes.get_playlist()
                self._updateDisplayForCurrentSong()
            else:
                logging.debug("Playlist Fetch failed.")
                refresh = 10
                self._playlist = {}
            self._dumpPlaylist()
            logging.debug("Playlist refresh in {} seconds".format(refresh))
            time.sleep(refresh)

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))# doesn't even have to be reachable
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def _showIpAddress(self):
        ip = self.get_ip()
        logging.debug('Getting IP Address of local machine {}'.format(ip))
        ipParts = ip.split('.')

        if len(ipParts) == 4:
            logging.debug('Writing IP to display')
            self._jp.Write4(ipParts[2])
            self._jp.Write3(ipParts[3])
        else:
            logging.debug('Unable to write IP to display')
            self._jp.Write4('----')
            self._jp.Write3('---')
    
    def _startItunes(self):
        while True:
            result = self._instance_itunes.start_itunes()
            if result == True:
                logging.debug('iTunes successfully started.')
                break
            else:
                logging.warning("iTunesStart ERROR. {}".format(self._instance_itunes.last_error))
            time.sleep(10) # Try again TODO: Make configurable

    def _updateDisplayForCurrentSong(self):
        persistentId = self._instance_itunes.reader.get_track_persistent_id()
        self._updateDisplayForSongPersistentId(persistentId)

    def _updateDisplayForSongPersistentId(self, persistentId):
        if persistentId == None:
            return False
        if self._playlist == None or len(self._playlist) == 0:
            logging.warning("Playlist not loaded yet.")
            return False
        if persistentId in self._playlist:
            self._jp.Write3(str(self._playlist[persistentId]['Index']+100))
            return True
        else:
            logging.info("Did NOT Find PersistentId {} in playlist!".format(persistentId))
            self._jp.Write3('---')
            return False

    def _iTunesUpdateCallback(self, itunes, key, value):
        #logging.debug("Info Update: {0} = {1}".format(key, value))
        if key == 'Persistent ID':
            if value != None:
                i = int(value,16)
                result = self._updateDisplayForSongPersistentId("{0:0{1}X}".format(i,16)) #Add Leading Zeros
                self._jp.Write4('')
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
            if index == 901:
                self._instance_itunes.control_volume_down()
            elif index == 902:
                self._instance_itunes.control_volume_up()
            elif index == 987:
                self._instance_itunes.control_prev()
            elif index == 989:
                self._instance_itunes.control_play_pause()
            elif index == 999:
                self._instance_itunes.control_next()
            elif index == 501:
                self._showIpAddress()
                return
            elif index == 502:
                self._dumpPlaylist()
            # If 300 thur 500, subtract 200 & play that song immediately. 
            elif 300 <= index < 500:
                index = index - 300
                if self._queue_song_by_index(index):
                    time.sleep(.5)
                    self._instance_itunes.control_next()
            elif 100 <= index < 300:
                self._queue_song_by_index(index - 100)
            else:
                logging.debug('Nothing defined for index {}'.format(index))

            self._reset_panel_display()

    def _dumpPlaylist(self):
        with open('/tmp/playlist_dump.txt', 'w') as dumpfile:
            pl = self._playlist
            if pl == None:
                dumpfile.write('playlist is None')
                return
            if len(pl) == 0:
                dumpfile.write('playlist is empty (zero records)')
                return
            for k in pl:
                logging.info  ("{}: PersistantId: {} Name: {}"  .format(str(pl[k]['Index']), k, pl[k]['Name']))
                dumpfile.write("{}: PersistantId: {} Name: {}\n".format(str(pl[k]['Index']), k, pl[k]['Name']))

    def _reset_panel_display(self):
        self._bufferJBSelection = ''
        self._jp.Led1Set(False)
        self._jp.Clear4()

    def get_persistId_from_index(self, index):
        item = [key for key in self._playlist.keys() if self._playlist[key]['Index']== index]
        if len(item) == 1:
            return item[0]
        return None

    def _queue_song_by_index(self, index):
        persistId = self.get_persistId_from_index(index)
        if persistId == None:
            logging.debug('No song for index {}'.format(index))
            return False
        else:
            logging.debug('selecting song for index {} persistentId: {}'.format(index, persistId))
            self._instance_itunes.queue_by_persistent_id(int(persistId, 16))
            return True

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
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S") #TODO Make logging level configurable
    logging.getLogger().setLevel(logging.DEBUG)
    start()
    #_testPanelDriver()
    #_testPlaylistFetch()
    # controller = JukeboxMainController()
    # time.sleep(30)
    # pl = controller._playlist
    # for k in pl:
    #     print("\t{} : Index: {} Title: {}".format(k, str(pl[k]['Index']), pl[k]['Name']))
