from serial import Serial
import time
import re
import threading
from collections import deque
import logging

class JukeboxPanelSerialDriver:
    """
    A class used to control the Jukebox LED/Keypad panel via Serial port via Arduino
    """
    def __init__(self):
        self._display3Line = 0
        self._display4Line = 0
        self._led0State = False
        self._led1State = False
        self._port = Serial(port='/dev/ttyUSB0', baudrate=115200, timeout=None)
        self._inputBuffer = ''
        self._queueSerialIn = deque([])
        """
        Callback Function when a button is pressed on the keypad.
        Has a single argument, str of the button pressed. (0-9, R, P)
        """
        self.buttonPushedCallback = None
        self._patternBTN = re.compile(r"BTN:([0-9]|R|P)", re.A)
        self._threadReadLoop = threading.Thread(target=self._read_from_port_loop)
        self._threadReadLoop.daemon = True
        self._threadReadLoop.start()
        time.sleep(2) # need to delay before port is open for writing. https://github.com/pyserial/pyserial/issues/329
        self._write('') # ready the arduino, clear any partial commands

    def __del__(self):
        logging.debug("JukeboxPanelSerialDriver destructor called.")
        if (self._port):
            if (self._port.is_open):
                self._port.flush()
                self._port.close()
                logging.debug('Port flushed and closed.')
            else:
                logging.debug('Port was not open.')
        else:
            logging.debug('No port defined.')

    def _read_from_port_loop(self):
        while True:
            c = self._port.read(size=1) # Attempt to read a character. Blocks based on timeout set on Serial object __init__
            if (len(c) > 0):
                #print("GOT CHAR! {0}".format(c))
                self._inputBuffer = (self._inputBuffer + (c.decode('ascii'))).replace(">\n", '') # Filter out the > prompt.
                parts =  self._inputBuffer.split("\n")  # Each response from arduino ends with \n. Split them all up into a list.
                if len(self._inputBuffer) > 10:
                    # Safety valve. No single respnose should be over 50 characters.
                    logging.warning("JukeboxPanelSerialDriver: inputBuffer > 50 {0} {1}".format(len(self._inputBuffer), self._inputBuffer))                
                    self._inputBuffer = '' # Reset the input buffer in emegency
                if len(parts) > 1:
                    # At least one new line (& response) was detected
                    self._queueSerialIn.extendleft(parts[:-1]) # Add all parts except the last (incomplete) one
                    self._inputBuffer = parts[-1] # Reset the buffer to the last (incomplete) response.
                    while len(self._queueSerialIn) > 0: # While there are responses in the queue, process them.
                        raw = self._queueSerialIn.pop() # Get the earliest response
                        m = self._patternBTN.search(raw)    # Does this match a button pressed response?
                        if m and self.buttonPushedCallback: # if a BTN: response was found and a callback registered,
                            self.buttonPushedCallback(m.group(1))   # call it with the button.

    # Write out the string to the 3 digit display
    def Write3(self, message):
        self._write('w3 ' + message)

    # Clear the 3 digit display
    def Clear3(self):
        self.Write3('   ')

    # Write out the string to the 4 digit display
    def Write4(self, message):
        self._write('w4 ' + message)

    # Clear the 4 digit display
    def Clear4(self):
        self.Write4('    ') # Leave LED0 and LED1 alone
    
    def _write(self, value):
        self._port.write((value + '\r\n').encode('ascii'))
        self._port.flush()

    # Turn on or off LED0
    def Led0Set(self, value): 
        if (value):
            self._write('led0 1')
        else:
            self._write('led0')

    # Turn on or off LED1
    def Led1Set(self, value):
        if (value):
            self._write('led1 1')
        else:
            self._write('led1')
    
    # Turn off all LEDs
    def Off(self):
        self._write('off')
    
    # Blank all 7 segment LEDs. LED0 and LED1 unaffected
    def Clear(self):
        self._write('c')

def _testDisplay():
    jp = JukeboxPanelSerialDriver()
    jp.Off()
    #jp.Clear()
    jp.Write3("123")
    jp.Write4("4567")
    #jp.Led0Set(True)    
    time.sleep(3)
    #jp.Led0Set(False)  
    #jp.Led1Set(True)
    jp.Write3("456")
    jp.Write4("7890")
    time.sleep(3)
    jp.Off()

def _testKeypad():
    jp = JukeboxPanelSerialDriver()
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

if __name__ == '__main__':
    _testDisplay()
    #_testKeypad()
