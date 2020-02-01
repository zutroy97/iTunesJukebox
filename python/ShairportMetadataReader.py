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

class ShairportMetadataReader:
    def __init__(self):
        self._patternGetKeyValue = re.compile(r'(.*?)\:\s*\"?(.*)\"',re.A)
        self.info_available_callback = None
        self._stored_fields = {}
        self._popen = None
        self._lock = threading.Lock()
        self._sessionId = None

    def _read_pipe(self, cmd):
        self._popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
        yield 'parser_event: "Pipe Open"'
        for stdout_line in iter(self._popen.stdout.readline, ""):
            yield stdout_line 

    def _get_key_value(self, line):
        m = self._patternGetKeyValue.search(line)
        if m:
            #print("FOUND {} : {}".format(m.group(1), m.group(2)))
            kvp = KeyValuePair(m.group(1), m.group(2))
            return kvp
        else:
            return None

    def _set_field_if_key_matches(self, key, kvp):
        if key != kvp.key:
            return
        with self._lock:
            self._stored_fields[key] = kvp.value
        
    def get_session_id(self):
        return self._sessionId

    def _setSessionId(self, value):
        self._sessionId = value

    def refresh_iTunes_session_id(self, force=False):
        if (force == False ) and (self.get_session_id() != None):
            return
        result = self._make_iTunes_request("login", { "pairing-guid" : "0x0000000000000001"})
        if result == None:
            logging.debug("Unable to make session request.")
            return False
        d = iTunesDecoder.DacpDecoder()
        dacpResult = d.decode(list(result))
        sessionId = dacpResult['mlog']['mlid']
        logging.debug("refresh_iTunes_session_id: SessionId = {0}".format(sessionId))
        self._setSessionId(sessionId)

    def _make_iTunes_request(self, path, params=None, headers = None):
        if persistentId == None :
            logging.debug("queue_by_persistent_id: No PersistantId specified.")
            return False
        if self.reader.get_active_remote_token() == None:
            logging.debug("queue_by_persistent_id: Active-Remote token not set.")
            return False
        url = self.get_iTunes_base_url()
        if url == None:
            logging.debug("_make_iTunes_request - Don't know iTunes URL")
            return None        
        urlParams = ''
        req = None

        if params == None:
            url = "{0}{1}".format(url, path)
        else:
            url = "{0}{1}?{2}".format(url, path, urllib.parse.urlencode(params))            
        req = urllib.request.Request(url)

        if headers != None:
            req.headers = headers
        ### Uncomment for advanced logging of requests/responses from iTunes
        # logging.debug("_make_iTunes_request: url = {}".format(req.full_url))
        # handler = urllib.request.HTTPHandler(debuglevel=10)
        # opener = urllib.request.build_opener(handler)
        # return opener.open(req).read()
        ### END of Uncomment for advanced logging of requests/responses from iTunes
        with urllib.request.urlopen(req) as response:
            results = response.read()
        return results

    def get_iTunes_base_url(self):
        ip = self.get_ip_address()
        port = self.get_port()
        if ip == None :
            logging.debug("get_iTunes_base_url - No ip address found")
            return None
        if port == None :
            logging.debug("get_iTunes_base_url - No port address found")
            return None
        return "http://{}:{}/".format(ip, port)

    def get_port(self):
        return self._get_value('"ssnc" "dapo"')

    def get_track_persistent_id(self):
        return self._get_value('Persistent ID')

    def get_dacp_id(self):
        return self._get_value('"ssnc" "daid"')

    def get_active_remote_token(self):
        return self._get_value('"ssnc" "acre"')

    def get_ip_address(self):
        return self._get_value("Client's IP")

    def _get_value(self, key):
        with self._lock:
            if key in self._stored_fields:
                return self._stored_fields[key]
            return None

    def loop(self):
        keepOnKeepingOn = 1
        while keepOnKeepingOn:
            try:
                for line in self._read_pipe(["/home/pi/pipe-metadata.sh"]):
                    #logging.debug("ShairportMetaReader received line: {}".format(line))
                    kvp = self._get_key_value(line)
                    if kvp:
                        #logging.debug("PUBLISH {} : {}".format(kvp.key, kvp.value))
                        self._set_field_if_key_matches('"ssnc" "dapo"', kvp) # iTunes Port Number
                        self._set_field_if_key_matches('"ssnc" "daid"', kvp) # DACP-ID 
                        self._set_field_if_key_matches('"ssnc" "acre"', kvp) 
                        self._set_field_if_key_matches("Client's IP", kvp) 
                        if kvp.key == 'Persistent ID':
                            kvp.value = kvp.value.upper()
                            self._set_field_if_key_matches('Persistent ID', kvp)
                        # elif kvp.key == "Client's IP":
                        #     self.refresh_iTunes_session_id()
                        # elif kvp.key == '"ssnc" "dapo"':
                        #     self.refresh_iTunes_session_id()

                        if self.info_available_callback:
                            self.info_available_callback(self, kvp.key, kvp.value)
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
    # if key == 'Title':
    #     itunes.queue_by_persistent_id(0x9E73AFE715844D08)

def _test():
    p = ShairportMetadataReader()
    p.info_available_callback = _testInfoAvailableCallback
    p.loop()

# def _testInfoAvailableCallback_Session(itunes, key, value):
#     print("Info Update: {0} = {1}".format(key, value))
#     if key == "Client's IP" or key == "":
#         self.refresh_iTunes_session_id()

# def _testGettingSession:
#     p = ParseShairportSyncMetadata()
#     p.InfoAvailableCallback = _testInfoAvailableCallback_Session
#     p.loop()

if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.DEBUG)    
    _test()