# Copyright []
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
### BEGIN NODE INFO
[info]
name = Helium_level_meter
version = 1.0
description = Arduino MKRZero turns on and off the helium level meter AMI 110 A and reads the output voltage.
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""


from labrad.server import setting, Signal
from labrad.devices import DeviceServer,DeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor, defer
import labrad.units as units
from labrad.types import Value
import numpy as np
import time
#from exceptions import IndexError

TIMEOUT = Value(5,'s')
BAUD    = 115200

def threeByteToIntAdc(DB1,DB2,DB3): # This gives a 16 bit integer (between +/- 2^16)
  return 65536*DB1 + 256*DB2 + DB3

def map2(x, in_min, in_max, out_min, out_max):
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;


class AMI110Wrapper(DeviceWrapper):

    @inlineCallbacks
    def connect(self, server, port):
        """Connect to a device."""
        print("connecting to %s on port %s..." % (server.name, port))
        self.server = server
        self.ctx = server.context()
        self.port = port
        self.ramping = False
        p = self.packet()
        p.open(port)
        p.baudrate(BAUD)
        p.read()  # clear out the read buffer
        p.timeout(TIMEOUT)
        print(" CONNECTED ")
        yield p.send()
        
    def packet(self):
        """Create a packet in our private context."""
        return self.server.packet(context=self.ctx)

    def shutdown(self):
        """Disconnect from the serial port when we shut down."""
        return self.packet().close().send()

    @inlineCallbacks
    def write(self, code):
        """Write a data value to the heat switch."""
        yield self.packet().write(code).send()

    @inlineCallbacks
    def read(self):
        p=self.packet()
        p.read_line()
        ans=yield p.send()
        returnValue(ans.read_line)

    @inlineCallbacks
    def readByte(self,count):
        p=self.packet()
        p.read(count)
        ans=yield p.send()
        returnValue(ans.read)

    @inlineCallbacks
    def in_waiting(self):
        p = self.packet()
        p.in_waiting()
        ans = yield p.send()
        returnValue(ans.in_waiting)

    @inlineCallbacks
    def reset_input_buffer(self):
        p = self.packet()
        p.reset_input_buffer()
        ans = yield p.send()
        returnValue(ans.reset_input_buffer)

    @inlineCallbacks
    def timeout(self, time):
        yield self.packet().timeout(time).send()

    @inlineCallbacks
    def query(self, code):
        """ Write, then read. """
        p = self.packet()
        p.write_line(code)
        p.read_line()
        ans = yield p.send()
        returnValue(ans.read_line)
        


class HeLevelMeterServer(DeviceServer):
    name = 'Helium_level_meter'
    deviceName = 'Arduino_He_level'
    deviceWrapper = AMI110Wrapper

    @inlineCallbacks
    def initServer(self):
        print("loading config info...")
        self.reg = self.client.registry()
        yield self.loadConfigInfo()
        print("done.")
        print(self.serialLinks)
        yield DeviceServer.initServer(self)

    @inlineCallbacks
    def loadConfigInfo(self):
        reg = self.reg
        yield reg.cd(['', 'Servers', 'he_level_meter', 'Links'], True)
        dirs, keys = yield reg.dir()
        p = reg.packet()
        print(" created packet")
        print("printing all the keys",keys)
        for k in keys:
            print("k=",k)
            p.get(k, key=k)
            
        ans = yield p.send()
        print("ans=",ans)
        self.serialLinks = dict((k, ans[k]) for k in keys)

    @inlineCallbacks
    def findDevices(self):
        """Find available devices from list stored in the registry."""
        devs = []
        for name, (serServer, port) in self.serialLinks.items():
            if serServer not in self.client.servers:
                continue
            server = self.client[serServer]
            print(server)
            print(port)
            ports = yield server.list_serial_ports()
            print(ports)
            if port not in ports:
                continue
            devName = '%s (%s)' % (serServer, port)
            devs += [(devName, (server, port))]

       # devs += [(0,(3,4))]
        returnValue(devs)

    
    @setting(100)
    def connect(self,c,server,port):
        dev=self.selectedDevice(c)
        yield dev.connect(server,port)

    @setting(104,returns='v[]')
    def get_voltage(self,c):
        """
        Returns voltage proportional to helium level from 0 to 3.3 V
        """
        dev=self.selectedDevice(c)
        yield dev.write("GET_V\r")
        ans = yield dev.read()
        returnValue(float(ans))

    @setting(105,returns='v[]')
    def get_length(self,c):
        """
        Returns the lenght in inches.
        """
        dev=self.selectedDevice(c)
        yield dev.write("GET_LENGTH\r")
        ans = yield dev.read()
        returnValue(float(ans))

    @setting(106,returns='v[]')
    def get_percent(self,c):
        """
        Return helium level percentage.
        """
        dev=self.selectedDevice(c)
        yield dev.write("GET_PERCENT\r")
        ans = yield dev.read()
        returnValue(float(ans))

    @setting(107,returns='i')
    def turn_on(self,c):
        """
        Turn on the helium level meter.
        """
        dev=self.selectedDevice(c)
        yield dev.write("TURN_ON\r")
        ans = yield dev.read()
        returnValue(int(ans))

    @setting(108,returns='i')
    def turn_off(self,c):
        """
        Turns off the helium level meter.
        """
        dev=self.selectedDevice(c)
        yield dev.write("TURN_OFF\r")
        ans = yield dev.read()
        returnValue(int(ans))

    @setting(109,returns='s')
    def ID(self,c):
        dev=self.selectedDevice(c)
        yield dev.write("*IDN?\n")
        ans = yield dev.read()
        returnValue(ans)

    @setting(9002)
    def read(self,c):
        dev=self.selectedDevice(c)
        ret=yield dev.read()
        returnValue(ret)

    @setting(9003)
    def write(self,c,phrase):
        dev=self.selectedDevice(c)
        yield dev.write(phrase)

    @setting(9004)
    def query(self,c,phrase):
        dev=self.selectedDevice(c)
        yield dev.write(phrase)
        ret = yield dev.read()
        returnValue(ret)
    
    @setting(9005,time='v[s]')
    def timeout(self,c,time):
        dev=self.selectedDevice(c)
        yield dev.timeout(time)

    @setting(9100)
    def send_read_requests(self,c):
        dev = self.selectedDevice(c)
        for port in [0,1,2,3]:
            yield dev.write("GET_ADC,%i\r"%port)
            ans = yield dev.read()
            self.sigInputRead([str(port),str(ans)])

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = defer.Deferred()
        reactor.callLater(secs,d.callback,'Sleeping')
        return d

__server__ = HeLevelMeterServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
