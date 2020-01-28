import time
from gpiozero import LED

class JukeboxPanelGpioDriver:
    def __init__(self):
        self._build_Jukebox_Characters()
        self._build_Jukebox_Keypad_Map()
        self._clockPin = LED("GPIO23")
        self._displayEnablePin = LED("GPIO24")
        self._display4Pin = LED("GPIO25")
        self._display3Pin = LED("GPIO8")
        self._keypadMatrixCpin = -1
        self._outputPin1 = -1
        self._outputPin2 = -1

        self._display3Line = 0
        self._display4Line = 0
        self._led0State = False
        self._led1State = False

        self._lastKeypadReadTime = 0
        self._lastKeypadSent = '_'
        self._lastKeypadRead = '_'

    # Value needed to display char c
    def GetCharacterMap(self, char):    
        if (char not in self._characterMap):
            return 8 # Char is not defined (return underscore)
        return self._characterMap[char]

    # Write out _displayLine3 and _displayLine4 values to the display
    def UpdateDisplay(self):
        mask0 = debug0 = debug1 = i = 0
        b0 = b1 = False
        self._digitalWrite(self._displayEnablePin, True)
        self._writeBit(True, True) # Start packet
        self._delayForClock()
        for i in range(32):
            mask0 = 1 << i
            b0 = (mask0 & self._display3Line) > 0
            b1 = (mask0 & self._display4Line) > 0
            debug0 = (debug0 << 1) | b0
            debug1 = (debug1 << 1) | b1
            self._writeBit(b0, b1)
        # 33 bits written. Must write a total of 36 bits to get chips to latch
        for i in range(4):
            self._writeBit(False, False)
        # All 36 bits written
        #print()
        self._debug('UpdateDisplay')
        self._debug("_display3Line", self._display3Line)
        self._debug("_display4Line", self._display4Line)
        self._debug("debug0", debug0)
        self._debug("debug1", debug1)
        self._digitalWrite(self._displayEnablePin, False)

    def _debug(self, key, value=None):
        return
        if (value == None):
            print (key)
        else:
            print("{0:{1}}: {2:#0{3}X}".format(key, 14, value, 10))

    # Write out the string to the 3 digit display
    def Write3(self, message):
        self.Write(message, False)

    # Clear the 3 digit display
    def Clear3(self):
        self._display3Line = 0

    # Write out the string to the 4 digit display
    def Write4(self, message):
        self.Write (message, True)

    # Clear the 4 digit display
    def Clear4(self):
        self._display4Line &= 0xE0000000 # Leave LED0 and LED1 alone
    
    # Write this value (uint32_t) to the _displayLine3
    def SetRawValue3(self, value):  
        self._display3Line = value
        
    # Write this value (uint32_t) to the _displayLine3
    def SetRawValue4(self, value):  
        self._display4Line = value

    # Turn on or off LED0
    def Led0Set(self, value): 
        self._led0State = value
        if (value):
            self._display4Line |= 0x80000000
        else:
            self._display4Line &= ~0x80000000
        self.UpdateDisplay()

    # Turn on or off LED1
    def Led1Set(self, value):
        self._led1State = value
        if (value):
            self._display4Line |= 0x60000000
        else:
            self._display4Line &= ~0x60000000
        self.UpdateDisplay()

    # get the (uint16_t) keypad button pressed
    def GetCurrentKeypadValue(self):
        result = 0 # uint16_t
        self._digitalWrite(self._displayEnablePin, False)
        for i in range(8):
            self._digitalWrite(self._display4Pin, (i & 0x01))
            self._digitalWrite(self._display3Pin, (i & 0x02))
            self._digitalWrite(self._keypadMatrixCpin, (i & 0x04))
            result |= (self._digitalRead(self._outputPin1) << i)
            result |= (self._digitalRead(self._outputPin2) << (i + 8))
        self._digitalWrite(self._displayEnablePin, True)
        return result

    # decode the raw (uint16_t) value of the keypad
    def GetCurrentKeypadLetter(self, raw):
        if (raw not in self._keypad_map):
            return '_' # Not found
        return self._keypad_map[raw]

    # Get the time in milliseconds
    def _millis(self):
        return time.time() * 1000

    # Get the value of the Jukebox Panel button currently being pressed.
    # Returns '_' if nothing is pressed OR key press was already registered.
    # Prevents user from just holding down button for multiple identical values.
    def GetKey(self):
        thisKey = self.GetCurrentKeypadLetter(self.GetCurrentKeypadValue())
        # Is this reading different then the last reading?
        if (thisKey != self._lastKeypadRead):
            self._lastKeypadReadTime = self._millis()
            self._lastKeypadRead = thisKey

        # has it been more then 50ms the last reading?
        if (self._millis() - self._lastKeypadReadTime) > 50:
            # Time is up!
            if thisKey != self._lastKeypadRead:
                # last key has changed; Get new value on next reading
                # Prevents user from holding down button to make multiple entries
                self._lastKeypadRead = '_'
            elif self._lastKeypadSent != thisKey:
                # Button has been held down more then 50ms; debouncing complete
                self._lastKeypadSent = thisKey
                return thisKey
        return '_'
            

    # Turn off all LEDs
    def Off(self):
        self._display3Line = 0
        self._display4Line = 0
        self._led0State = False
        self._led1State = False
        self.UpdateDisplay()

    # Blank all 7 segment LEDs. LED0 and LED1 unaffected
    def Clear(self):
        self.Clear3()
        self.Clear4()
        self.UpdateDisplay()

    def Write(self, message, isDisplay4):
        message = str(message) # in case a number is passed in
        rmessage = message[::-1] # Reverse the message
        #print("message : {0}".format(message))
        #print("rmessage: {0}".format(rmessage))
        message = rmessage[:3]
        display = 0
        if (isDisplay4):
            message = rmessage[:4]
        #print("trimmed message : {0}".format(message))
        for i in range(len(message)):
            display = (display << 7 ) | self.GetCharacterMap(message[i])
        self._debug("display", display)
        if (isDisplay4):
            if self._led0State:
                display |= 0x80000000
            if self._led1State:
                display |= 0x60000000
            self._display4Line = display
        else:
            self._display3Line = display
        self.UpdateDisplay()

    def _writeBit(self, display3Bit, display4Bit):
        self._digitalWrite(self._display3Pin, display3Bit)
        self._digitalWrite(self._display4Pin, display4Bit)
        self._digitalWrite(self._clockPin, False)
        self._delayForClock() ## sleep 400 micro-seconds
        self._digitalWrite(self._clockPin, True)

    # Wait for jukebox panel clock to settle
    def _delayForClock(self):
        pass
        #time.sleep(4.0E-6)## sleep 400 micro-seconds
        #time.sleep(400/1000000.0) 

    # Set pin HIGH/True or LOW/False
    def _digitalWrite(self, pin, value):
        if value:
            pin.on()
        else:
            pin.off()

    # Read the current state of the pin
    def _digitalRead(self, pin):
        pass

    def _build_Jukebox_Keypad_Map(self):
        self._keypad_map = { 
            0x7dff: 'P',
            0xFDDF: '1',
            0xfcff: '2',
            0xfdf7: '3',
            0xfdfc: '4',
            0xedff: '5',
            0xfdef: '6',
            0xfd3f: '7',
            0xF5FF: '8',
            0xFDFB: '9',
            0xDDFF: '0',
            0xBDFF: 'R'
        }
    def _build_Jukebox_Characters(self):
        self._characterMap = {
            ' ': 0,
            '0': 119,
            '1': 65,
            '2': 59,
            '3': 107,
            '4' : 77,
            '5' : 110,
            '6' : 126,
            '7' : 67,
            '8' : 127,
            '9' : 111,
            'a' : 95,
            'b' : 124,
            'c' : 54,
            'd' : 121, 
            'e' : 62,  
            'f' : 30,  
            'g' : 111, 
            'h' : 92,  
            'i' : 20,  
            'j' : 113, 
            'k' : 93,  
            'l' : 52,  
            'm' : 82,  
            'n' : 88,  
            'o' : 120, 
            'p' : 31,  
            'q' : 79,  
            'r' : 24 , 
            's' : 110, 
            't' : 60,  
            'u' : 117, 
            'v' : 112, 
            'w' : 37,  
            'x' : 93,  
            'y' : 109, 
            'z' : 59              
        }
def _test():
    jp = JukeboxPanelGpioDriver()
    jp.Clear()

    x = 0
    y = 1050
    while True:
        jp.Write3("{:3}".format(x))
        jp.Write4("{:4}".format(y))
        x = x + 1
        y = y - 1
        time.sleep(.50)

    #jp.Led0Set(True)
    #jp.SetRawValue3(0xff00)
    #jp.UpdateDisplay()
    jp.Write3(" 23")
    jp.Write4("4567")
    jp.Led0Set(True)
    #jp.Led1Set(False)
#    print(jp.GetCharacterMap('0'))
#    print (jp.GetCharacterMap('9'))
#    print (jp.GetCharacterMap('*'))
#    print (jp.GetCurrentKeypadLetter(0x7dff))
#    print (jp.GetCurrentKeypadLetter(0xDDFF))

if __name__ == '__main__':
    _test()