#!/usr/bin/python3

import sys, struct, re

class DacpDecoder:
    def __init__(self):
        self.raw = []
        self.group = ['cmst','mlog','agal','mlcl','mshl','mlit','abro','abar','apso','caci','avdb','cmgt','aply','adbs','cmpa']
        self.rebinary = re.compile('[^\x20-\x7e]')
        self.result = {}

    def format(self, c):
        if ord(c) >= 128:
            return "(byte)0x%02x"%ord(c)
        else:
            return "0x%02x"%ord(c)

    def read(self, queue, size):
        pull = bytearray(queue[0:size])
        del queue[0:size]
        return pull

    def ashex(self,s):
        x =  ''.join(["{0:02x}".format(c) for c in s ])
        return x

    def asbyte(self, s):
        return struct.unpack('>B', s)[0]
    
    def asint(self, s): 
        return struct.unpack('>I', s)[0]
    
    def aslong(self, s): 
        return struct.unpack('>Q', s)[0]

    def decode(self, message):
        self.result =  self._decode(message, len(message), 0)
        return self.result

    def _decode(self, raw, handle, indent):
        result = {}
        while handle >= 8:
            # read word data type and length
            ptype = self.read(raw, 4).decode()
            x = self.read(raw, 4)
            plen = self.asint(x)
            #print("ptype: {} plen: {}".format(ptype, plen))
            handle -= 8 + plen
            
            # recurse into groups
            if ptype in self.group:
                #print("{} {} --+".format('\t' * indent, ptype))
                result[ptype] = self._decode(raw, plen, indent + 1)
                continue
            
            # read and parse data
            pdata = self.read(raw, plen)
            nice = "{}".format(self.ashex(pdata))
            result[ptype] = self.asint(pdata)

            # if plen == 1:
            #     nice = "{} == {}".format(self.ashex(pdata), self.asbyte(pdata))
            # if plen == 4: nice = "{} == {}".format(self.ashex(pdata), self.asint(pdata))
            # if plen == 8: nice = "{} == {}".format(self.ashex(pdata), self.aslong(pdata))
            
            # if self.rebinary.search(pdata) is None:
            #     nice = pdata
            #print("{} {} {} {}".format('\t' * indent, ptype.ljust(6), str(plen).ljust(6), nice))
        return result

if __name__ == '__main__':
    raw = [0x6d,0x6c,0x6f,0x67,0x00,0x00,0x00,0x18,0x6d,0x73,0x74,0x74,0x00,0x00,0x00,0x04,0x00,0x00,0x00,0xc8,0x6d,0x6c,0x69,0x64,0x00,0x00,0x00,0x04,0x27,0x32,0x1b,0x54]
    d = DacpDecoder()
    result = d.decode(raw)
    print(result)
    print(result['mlog']['mlid'])
    print("{0:x}".format(result['mlog']['mlid']))