
from datetime import datetime
try:
    from Crypto.Cipher import AES
except ImportError as e:
    import pyaes

import time
import random
import socket

from device import device

# This in an implementation for eControl with devices of the type 'SPMini2' ID code 0x2728


PACKAGE_SIZE = 45

# indices for filling in the message buffer
IDX_TIMEZONE = 0x06
IDX_YEAR     = 0x0A
IDX_TIME_SEC = 0x0C
IDX_TIME_MIN = 0x0D
IDX_TIME_HRS = 0x0E
IDX_WEEK_NUM = 0x0F
IDX_DAY      = 0x10
IDX_MONTH    = 0x11

IDX_PORT     = 0x1A

IDX_CMD      = 0x26 

# Posible values for IDX_CMD
CMD_Hello    = 0x6
CMD_Discover = 0x1a
CMD_Join     = 0x14
CMD_Auth     = 0x65
CMD_Command  = 0x6a



class sp2mini2(device):

    def __init__ (self, host, mac):
        device.__init__(self, host, mac)
        self.type = "SP2Mini2"


    def build_static_packet(self, command, payload):
        self.count = (self.count + 1) & 0xffff
        package_size = 0x38
        packet = bytearray(package_size)

        for i in range(0,package_size):
            packet[i] = 0

        packet[0x00] = 0x5a
        packet[0x01] = 0xa5
        packet[0x02] = 0xaa
        packet[0x03] = 0x55
        packet[0x04] = 0x5a
        packet[0x05] = 0xa5
        packet[0x06] = 0xaa
        packet[0x07] = 0x55

        # device Id
        packet[0x24] = 0x28
        packet[0x25] = 0x27

        packet[0x26] = command

        packet[0x28] = self.count & 0xff
        packet[0x29] = self.count >> 8
        packet[0x2a] = self.mac[0]
        packet[0x2b] = self.mac[1]
        packet[0x2c] = self.mac[2]
        packet[0x2d] = self.mac[3]
        packet[0x2e] = self.mac[4]
        packet[0x2f] = self.mac[5]
        packet[0x30] = self.id[0]
        packet[0x31] = self.id[1]
        packet[0x32] = self.id[2]
        packet[0x33] = self.id[3]

        # pad the payload for AES encryption
        if len(payload)>0:
          numpad=(len(payload)//16+1)*16
          payload=payload.ljust(numpad,b"\x00")

        checksum = 0xbeaf
        for i in range(len(payload)):
          checksum += payload[i]
          checksum = checksum & 0xffff

        payload = self.encrypt(payload)

        packet[0x34] = checksum & 0xff
        packet[0x35] = checksum >> 8

        for i in range(len(payload)):
          packet.append(payload[i])

        checksum = 0xbeaf
        for i in range(len(packet)):
          checksum += packet[i]
          checksum = checksum & 0xffff
        packet[0x20] = checksum & 0xff
        packet[0x21] = checksum >> 8

        starttime = time.time()
        with self.lock:
          while True:
            try:
              self.cs.sendto(packet, self.host)
              self.cs.settimeout(1)
              response = self.cs.recvfrom(2048)
              break
            except socket.timeout:
              if (time.time() - starttime) > self.timeout:
                raise
        return bytearray(response[0])

    # overwritting the method adapted to SP2Mini2
    def send_packet(self, command, payload):
        self.count = (self.count + 1) & 0xffff

        package_size = 0x38
        packet = bytearray(package_size)

        for i in range(0,package_size):
            packet[i] = 0

        packet[0x00] = 0x5a
        packet[0x01] = 0xa5
        packet[0x02] = 0xaa
        packet[0x03] = 0x55
        packet[0x04] = 0x5a
        packet[0x05] = 0xa5
        packet[0x06] = 0xaa
        packet[0x07] = 0x55

        packet[0x24] = 0x28
        packet[0x25] = 0x27
        packet[0x26] = command

        packet[0x28] = self.count & 0xff
        packet[0x29] = self.count >> 8
        packet[0x2a] = self.mac[0]
        packet[0x2b] = self.mac[1]
        packet[0x2c] = self.mac[2]
        packet[0x2d] = self.mac[3]
        packet[0x2e] = self.mac[4]
        packet[0x2f] = self.mac[5]
        packet[0x30] = self.id[0]
        packet[0x31] = self.id[1]
        packet[0x32] = self.id[2]
        packet[0x33] = self.id[3]

        # pad the payload for AES encryption
        if len(payload)>0:
            numpad=(len(payload)//16+1)*16
            payload=payload.ljust(numpad,b"\x00")

        checksum = 0xbeaf
        for i in range(len(payload)):
            checksum += payload[i]
            checksum = checksum & 0xffff

        payload = self.encrypt(payload)

        packet[0x34] = checksum & 0xff
        packet[0x35] = checksum >> 8

        for i in range(len(payload)):
          packet.append(payload[i])

        checksum = 0xbeaf
        for i in range(len(packet)):
            checksum += packet[i]
            checksum = checksum & 0xffff

        packet[0x20] = checksum & 0xff
        packet[0x21] = checksum >> 8

        starttime = time.time()
        print "Dump buffer to send..."
        print dump_hex_buffer(packet)

        with self.lock:
            while True:
                try:
                    self.cs.sendto(packet, self.host)
                    self.cs.settimeout(1)
                    response = self.cs.recvfrom(2048)
                    break
                except socket.timeout:
                    if (time.time() - starttime) > self.timeout:
                        raise
        return bytearray(response[0])



    def flip_the_switch(self, status=1):
        
        print "Switching to %s" % status
        local_ip_address = None

        if local_ip_address is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 53))  # connecting to a UDP address doesn't send packets
            local_ip_address = s.getsockname()[0]

        address = local_ip_address.split('.')
        cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        cs.bind((local_ip_address,0))
        port = cs.getsockname()[1]
        starttime = time.time()

        devices = []

        timezone = int(time.timezone/-3600)
        packet = bytearray( PACKAGE_SIZE )

        # initialize buffer:
        for i in range(len(packet)):
            packet[i] = 0

        year = datetime.now().year

        if timezone < 0:
            packet[IDX_TIMEZONE]     = 0xff + timezone - 1
            packet[IDX_TIMEZONE + 1] = 0xff
            packet[IDX_TIMEZONE + 2] = 0xff
            packet[IDX_TIMEZONE + 3] = 0xff
        else:
            packet[IDX_TIMEZONE] = timezone
            packet[IDX_TIMEZONE + 1] = 0
            packet[IDX_TIMEZONE + 2] = 0
            packet[IDX_TIMEZONE + 3] = 0

        packet[IDX_YEAR]        = year & 0xff
        packet[IDX_YEAR + 1]    = year >> 8

        packet[IDX_TIME_SEC] = datetime.now().second
        packet[IDX_TIME_MIN] = datetime.now().minute
        packet[IDX_TIME_HRS] = datetime.now().hour
        packet[IDX_WEEK_NUM] = datetime.now().isoweekday()
        packet[IDX_DAY]      = datetime.now().day
        packet[IDX_MONTH]    = datetime.now().month
        packet[0x12] = 0
        packet[0x13] = 0
        packet[0x14] = 0
        packet[0x15] = 0

        packet[0x16] = int(address[0])
        packet[0x17] = int(address[1])
        packet[0x18] = int(address[2])
        packet[0x19] = int(address[3])
             
        packet[IDX_PORT]     = port & 0xff
        packet[IDX_PORT + 1] = port >> 8
        packet[0x1C] = 0
        packet[0x1D] = 0
        

        packet[0x24] = 6
        checksum = 0xbeaf

        for i in range(len(packet)):
            checksum += packet[i]

        checksum = checksum & 0xffff
        packet[0x1E] = checksum & 0xff
        packet[0x1F] = checksum >> 8
        print "Checksum: %x " % checksum
        print "Sending package"

        response = self.send_packet(CMD_Command, packet)
        #cs.sendto(packet, ('255.255.255.255', 80))
        print "Dump buffer received..."
        print dump_hex_buffer(response)
        
        payload = self.decrypt(response[0x38:])
        print "Decode response..."
        if len(payload) > 0:
            print dump_hex_buffer(payload)
        print "Done"

def dump_hex_buffer(buf):
    str   = ""
    size  = len(buf)

    # print the index header in hex 0 to F
    str += "Index:\t"
    for j in xrange(0,0x10):
        str += "%2X " % j

    # print the buffer content in lines of 16 elements
    for i in range(0, size):
        # every 16 bytes we write a new line with the index
        idx = i % 16
        
        if idx == 0:
            str += "\n%04x\t" % i

        str += "%02x " %buf[i]

    return str

# Prints the buffer message on screen
def format_frame(msg):
    data  = []
    str   = ""
    size  = len(msg)
    print "Package of size: %s" % size

    for i in range(0, size):
        txt = "[%2d] %2X " % (i, msg[i])
        data.append( txt )

    for i in range(0, 10):
        for j in range(0,13):
            idx = (j*10)+i
            if idx < len(msg):
                str += data[ idx ]
        str += "\n"

    if size > 37:
        print "36-37 Device ID %x%x" % (msg[37],msg[36])

    if size > 57:
        print "Plug IP: 54-57 IP %s:%s:%s:%s" %(msg[54],msg[55],msg[56],msg[57])

    return str 
