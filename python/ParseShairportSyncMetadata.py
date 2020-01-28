#!/usr/bin/python3
import subprocess
import re
import time
import logging
import threading
import urllib.parse
import urllib.request
import DacpDecoder as iTunesDecoder


class KeyValuePair:
    def __init__(self, key, value):
        self.key = key
        self.value = value
    def __str__(self):
        return "{}: {}".format(self.key, self.value)

class ParseShairportSyncMetadata:
    def __init__(self):
        self._patternGetKeyValue = re.compile(r'(.*?)\:\s*\"?(.*)\"',re.A)
        self.InfoAvailableCallback = None
        self._storedFields = {}
        self._popen = None
        self._lock = threading.Lock()
        self._sessionId = None

    def execute(self, cmd):
        self._popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
        yield 'parser_event: "Pipe Open"'
        for stdout_line in iter(self._popen.stdout.readline, ""):
            yield stdout_line 

    def _getKeyValue(self, line):
        m = self._patternGetKeyValue.search(line)
        if m:
            #print("FOUND {} : {}".format(m.group(1), m.group(2)))
            kvp = KeyValuePair(m.group(1), m.group(2))
            return kvp
        else:
            return None

    def _setFieldIfKeyMatches(self, key, kvp):
        if key != kvp.key:
            return
        with self._lock:
            self._storedFields[key] = kvp.value
        
    def GetSessionId(self):
        return self._sessionId

    def _setSessionId(self, value):
        self._sessionId = value

    def QueueSongByPersistentId(self, persistentId):
        try:
            if persistentId == None :
                logging.debug("QueueSongByPersistentId: No PersistantId specified.")
                return False
            if self.GetSessionId() == None:
                logging.debug("QueueSongByPersistentId: SessionId not set.")
                return False
            if self.GetITunesActiveRemoteToken() == None:
                logging.debug("QueueSongByPersistentId: Active-Remote token not set.")
                return False
            headers = {"Active-Remote": self.GetITunesActiveRemoteToken()}
            # We have to build up the URL here since iTunes expects a VERY specific format about the query (can't escape single quotes or colon)
            url="ctrl-int/1/cue?command=add&query='dmap.persistentid:0x{0:X}'&mode=3&session-id={1}".format(persistentId, self.GetSessionId())
            logging.debug("QueueSongByPersistentId headers: {} url:{}".format(headers, url))

            result = self._makeITunesRequest(url, None, headers)
            if result == None:
                logging.warn("QueueSongByPersistentId: Unable to queue persistentId {}.".format(persistentId))
                return False
        except Exception as err:
            logging.error("QueueSongByPersistentId: Exception {}.".format(err))
            return False
        return True

    def RefreshITunesSessionId(self):
        result = self._makeITunesRequest("login", { "pairing-guid" : "0x0000000000000001"})
        if result == None:
            logging.debug("Unable to make session request.")
            return False
        d = iTunesDecoder.DacpDecoder()
        dacpResult = d.decode(list(result))
        sessionId = dacpResult['mlog']['mlid']
        logging.debug("RefreshITunesSessionId: SessionId = {0}".format(sessionId))
        self._setSessionId(sessionId)

    def _makeITunesRequest(self, path, params=None, headers = None):
        url = self.GetITunesBaseUrl()
        urlParams = ''
        req = None
        if url == None:
            logging.debug("_makeITunesRequest - Don't know iTunes URL")
            return None
        if params == None:
            url = "{0}{1}".format(url, path)
        else:
            url = "{0}{1}?{2}".format(url, path, urllib.parse.urlencode(params))            
        req = urllib.request.Request(url)

        if headers != None:
            req.headers = headers
        ### Uncomment for advanced logging of requests/responses from iTunes
        # logging.debug("_makeITunesRequest: url = {}".format(req.full_url))
        # handler = urllib.request.HTTPHandler(debuglevel=10)
        # opener = urllib.request.build_opener(handler)
        # return opener.open(req).read()
        ### END of Uncomment for advanced logging of requests/responses from iTunes
        with urllib.request.urlopen(req) as response:
            results = response.read()
        return results

    def GetITunesBaseUrl(self):
        ip = self.GetITunesIpAddress()
        port = self.GetITunesPortNumber()
        if ip == None :
            logging.debug("GetITunesBaseUrl - No ip address found")
            return None
        if port == None :
            logging.debug("GetITunesBaseUrl - No port address found")
            return None
        return "http://{}:{}/".format(ip, port)



    def GetITunesPortNumber(self):
        return self._getValueFromStoredFields('"ssnc" "dapo"')

    def GetITunesTrackPersistentId(self):
        return self._getValueFromStoredFields('Persistent ID')

    def GetITunesDacpId(self):
        return self._getValueFromStoredFields('"ssnc" "daid"')

    def GetITunesActiveRemoteToken(self):
        return self._getValueFromStoredFields('"ssnc" "acre"')

    def GetITunesIpAddress(self):
        return self._getValueFromStoredFields("Client's IP")

    def _getValueFromStoredFields(self, key):
        with self._lock:
            if key in self._storedFields:
                return self._storedFields[key]
            return None

    def loop(self):
        keepOnKeepingOn = 1
        while keepOnKeepingOn:
            try:
                for line in self.execute(["/home/pi/pipe-metadata.sh"]):
                    #print(line, end="")
                    kvp = self._getKeyValue(line)
                    if kvp:
                        #logging.debug("PUBLISH {} : {}".format(kvp.key, kvp.value))
                        self._setFieldIfKeyMatches('"ssnc" "dapo"', kvp) # iTunes Port Number
                        self._setFieldIfKeyMatches('"ssnc" "daid"', kvp) # DACP-ID 
                        self._setFieldIfKeyMatches('"ssnc" "acre"', kvp) 
                        self._setFieldIfKeyMatches("Client's IP", kvp) 
                        if kvp.key == 'Persistent ID':
                            kvp.value = kvp.value.upper()
                            self._setFieldIfKeyMatches('Persistent ID', kvp)
                        elif kvp.key == "Client's IP":
                            self.RefreshITunesSessionId()
                        elif kvp.key == '"ssnc" "dapo"':
                            self.RefreshITunesSessionId()

                        if self.InfoAvailableCallback:
                            self.InfoAvailableCallback(self, kvp.key, kvp.value)
                    else:
                        logging.debug("No match for line " + line)

            except KeyboardInterrupt:
                keepOnKeepingOn = 0
                break
            except Exception as err:
                logging.warning("Error reading from shairport-sync pipe: {}".format(err))
                if self._popen:
                    self._popen.stdout.close()
                    return_code = self._popen.wait()
                #time.sleep(2)

def _testInfoAvailableCallback(itunes, key, value):
    print("Info Update: {0} = {1}".format(key, value))
    if key == 'Title':
        itunes.QueueSongByPersistentId(0x9E73AFE715844D08)

def _test():
    p = ParseShairportSyncMetadata()
    p.InfoAvailableCallback = _testInfoAvailableCallback
    p.loop()

# def _testInfoAvailableCallback_Session(itunes, key, value):
#     print("Info Update: {0} = {1}".format(key, value))
#     if key == "Client's IP" or key == "":
#         self.RefreshITunesSessionId()

# def _testGettingSession:
#     p = ParseShairportSyncMetadata()
#     p.InfoAvailableCallback = _testInfoAvailableCallback_Session
#     p.loop()

if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.DEBUG)    
    _test()