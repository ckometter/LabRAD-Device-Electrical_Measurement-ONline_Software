# Copyright (C) 2011 Peter O'Malley/Charles Neill
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
name = Keithley_2450
version = 1.0.0
description = 

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg
from labrad import units
from labrad.server import setting
from labrad.gpib import GPIBManagedServer
from twisted.internet.defer import inlineCallbacks, returnValue


def trimReadValue(string):
    return float(string.rstrip('\\r\\n\'').lstrip('b\'').rstrip('\\n\''))

class Keithley_2450(GPIBManagedServer):
    name = 'Keithley_2450'
    deviceName = 'KEITHLEY INSTRUMENTS MODEL 2450' #set to the *Idn? resp

    def trimReadValue(self,string):
        return (string.rstrip('\\r\\n\'').lstrip('b\'').rstrip('\\n\''))

    @inlineCallbacks
    def inputMode(self, c):
        """returns the input mode. 0=A, 1=A-B, 2=I(10**6), 3=I(10**8)"""
        dev = self.selectedDevice(c)
        mode = yield dev.query('ISRC?')
        returnValue(int(self.trimReadValue(mode)))

    @inlineCallbacks
    def outputUnit(self, c):
        """returns a labrad unit, V or A, for what the main output type is. (R, X, Y)"""
        mode = yield self.inputMode(c)
        if mode < 2:
            returnValue(units.V)
        else:
            returnValue(units.A)

    @setting(10,'IDN',returns='s')
    def idn(self, c):
        """queries *IDN?"""
        dev = self.selectedDevice(c)
        mode = yield dev.query('*IDN?')
        returnValue(int(self.trimReadValue(mode)))

    @setting(11,'Output On',returns = 'i')
    def output_on(self,c):
        """Turns output on, returns 1 when finished"""
        dev = self.selectedDevice(c)
        yield dev.write(':OUTP ON')
        output = yield dev.query(':OUTP?')
        returnValue(int(self.trimReadValue(output)))

    @setting(12,'Output Off',returns = 'i')
    def output_off(self,c):
        """Turns output off, returns 0 when finished"""
        dev = self.selectedDevice(c)
        yield dev.write(':OUTP OFF')
        output = yield dev.query(':OUTP?')
        returnValue(int(self.trimReadValue(output)))

    @setting(13,'Output Status',returns = 'i')
    def output_status(self,c):
        """Returns 0 if output off, 1 if output on"""
        dev = self.selectedDevice(c)
        output = yield dev.query(':OUTP?')
        returnValue(int(self.trimReadValue(output)))

    @setting(14,'Measure Voltage',returns='v')
    def measure_voltage(self,c):
        """Sets the sensor to measure the voltage"""
        dev = self.selectedDevice(c)
        dat = yield dev.query(':MEAS:VOLT?')
        returnValue(float(self.trimReadValue(dat)))

    @setting(15,'Measure Current',returns='v')
    def measure_current(self,c):
        """Sets the sensor to measure the current"""
        dev = self.selectedDevice(c)
        dat = yield dev.query(':MEAS:CURR?')
        returnValue(float(self.trimReadValue(dat)))

    @setting(16,'Set Source Voltage',voltage='v')
    def set_source_voltage(self,c,voltage):
        """Assuming output is set to voltage already, sets voltage in Volts"""
        dev = self.selectedDevice(c)
        yield dev.write(':SOUR:VOLT' + ' ' +str(voltage))
    @setting(17,'Source Voltage')
    def source_voltage(self,c):
        """Set to source voltage (assumes output is off)"""
        dev = self.selectedDevice(c)
        yield dev.write(':SOUR:FUNC VOLT')

    @setting(18,'Set Source Current',current='v')
    def set_source_current(self,c,current):
        """Assuming output is set to current already, sets current in Amps"""
        dev = self.selectedDevice(c)
        yield dev.write(':SOUR:CURR' + ' ' +str(current))

    @setting(19,'Source Current')
    def source_current(self,c):
        """Set to source current (assumes output is off)"""
        dev = self.selectedDevice(c)
        yield dev.write(':SOUR:FUNC CURR')

    @setting(20, 'read input', returns='v')
    def read_input(self, c):
        """reads the input of """
        dev = self.selectedDevice(c)
        reading = yield dev.query(':READ?')
        returnValue(float(self.trimReadValue(reading)))

    @setting(21, 'fetch',returns='s')
    def fetch(self,c):
        dev = self.selectedDevice(c)
        reading = yield dev.query(':FETCH? "defbuffer1",READ,UNIT,SOUR,SOURUNIT')
        returnValue(str(self.trimReadValue(reading)))

__server__ = Keithley_2450()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)



"""Not implemented commands:

RSPL (?) {i}: set or query reference trigger (external only)

"""
