"""
### BEGIN NODE INFO
[info]
name = SR1
version = 0.0.0
description =

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""


from labrad.server import setting
from labrad.gpib import GPIBManagedServer
from twisted.internet.defer import inlineCallbacks, returnValue
import numpy as np

class SR1(GPIBManagedServer):
    name = 'SR1'
    deviceName = 'Stanford_Research_Systems SR1'
    graphID = None
    traceID = None
    chanID = None
    
    @setting(10, 'initialize_Spectral_Analyzer', returns='')
    def initialize_Spectral_Analyzer(self, c):
        '''
        Initializes the Spectral Analyzer. Default settings: 
        '''
        dev = self.selectedDevice(c)
        try:
            yield dev.write(':Ch(0):Source 1')
            yield dev.write(':Ch(0):AutoRange 1')
            yield dev.write(':Ch(0):Zin 0')
            yield dev.write(':Ch(0):Coupling 1')
            yield dev.write(':Ch(0):OptionalFilter 0')
            yield dev.write(':Alyzr(0):Function 1')
            yield dev.write(':Alyzr(0):Source 2')
            yield dev.write(':Alyzr(0):SampleRate 1')
            Rate = yield dev.query(':Alyzr(0):SampleRateRdg?')
            yield dev.write(':Alyzr(0):FFT:Lines 3')
            yield dev.write(':Alyzr(0):FFT:ShowAllLines 1')
            yield dev.write(':Alyzr(0):FFT:Baseband')
            yield dev.write(':Alyzr(0):FFT:Averaging 2')
            yield dev.write(':Alyzr(0):FFT:NumAverages 20')
            yield dev.write(':Alyzr(0):FFT:Window 8')
            yield dev.write(':Displays:DeleteAll')
            self.graphID = yield dev.query(':Displays:Newgraph?')
            self.traceID = yield dev.query('Displays:Graph(%s):AddTrace? 1111' %(self.graphID))
            yield dev.write(':Alyzr(0):FFT:ResetAvg')
            print Rate
        except Exception as inst:
            print 'Error Initializing Server: ', inst
            
    @setting(11, 'initialize_Squarewave_Generator', returns = '')
    def initialize_Squarewave_Generator(self, c):
        '''
        Initializes the Square Wave Generator. Default settings: 1kHz, 0nV
        '''
        dev = self.selectedDevice(c)
        try:
            yield dev.write(':AnlgGen:Ch(0):On 0')
            yield dev.write(':AnlgGen:Ch(1):On 0')
            yield dev.write(':AnlgGen:Ch(0):ClearWaveforms')
            yield dev.write(':AnlgGen:Ch(1):ClearWaveforms')
            yield dev.write(':AnlgGen:ConnectorConfig 0')
            yield dev.write(':AnlgGen:Zout 0')
            yield dev.write(':AnlgGen:Mono 1')
            yield dev.write(':AnlgGen:SampleRate 0')
            yield dev.write(':AnlgGen:Ch(0):Gain 100 %')
            yield dev.write(':AnlgGen:Ch(0):Invert 0')
            yield dev.write(':AnlgGen:BurstMode 0')
            self.chanID = yield dev.query(':AnlgGen:Ch(0):AddWaveform? 5')
        except Exception as inst:
            print 'Error Initializing Server: ', inst

    @setting(12, 'Identity', input = '', returns='s')
    def Identity(self, c, input = None):
        """
        Return the Identity of the object
        """
        dev = self.selectedDevice(c)
        resp = yield dev.query('*IDN?')
        returnValue(str(resp))

    @setting(13, 'Set_Analyzer_Function', AnalyzerIndex = 'i', FunctionIndex = 'i', returns = '')
    def Set_Analyzer_Function(self, c, AnalyzerIndex, FunctionIndex):
        """
        AnalyzerIndex: 0, 1;
        FunctionIndex: {azTimeDomDet=0 | azFFT=1 | azFFT2Ch=2 | azTHD=5 | azIMD=6 | azMultitone=7 | azJitter=9 | azHistogram=10}
        """
        dev = self.selectedDevice(c)
        yield dev.write(':Alyzr(%s):Function %s' %(AnalyzerIndex, FunctionIndex))
        
    @setting(14, 'Set_FFT_Converter', SampleRate = 'i: High BW(0) or High Res(1)', returns = '')
    def Set_FFT_Converter(self, c, SampleRate):
        """
        SampleRate: {azHiBW=0 | azHiRes=1}
        """
        dev = self.selectedDevice(c)
        yield dev.write(':Alyzr(0):SampleRate %s' %(SampleRate))
        
    @setting(15, 'Set_FFT_Bandwidth', Bandwidth = 'i: Bandwidth', returns = '')
    def Set_FFT_Bandwidth(self, c, Bandwidth):
        """
        Bandwidth: {fftFsDiv2=0 | fftFsDiv4=1 | fftFsDiv8=2 | fftFsDiv16=3 | fftFsDiv32=4 | fftFsDiv64=5 | fftFsDiv128=6 | fftFsDiv256=7 | fftFsDiv512=8 | fftFsDiv1024=9}
        """
        dev = self.selectedDevice(c)
        yield dev.write(':Alyzr(0):FFT:Span %s' %(Bandwidth))
        
    @setting(16, 'Set_FFT_Resolution', Resolution = 'i: Resolution', returns = '')
    def Set_FFT_Resolution(self, c, Resolution):
        """
        Resolution: {fftl32k=0 | fftl16k=1 | fftl8k=2 | fftl4k=3 | fftl2k=4 | fftl1k=5 | fftl512=6 | fftl256=7}
        """
        dev = self.selectedDevice(c)
        yield dev.write(':Alyzr(0):FFT:Lines %s' %(Resolution))
        
    @setting(17, 'Set_FFT_CenterFrequency', CenterFreq = 'v: center frequency in unit Hz', returns = '')
    def Set_FFT_CenterFrequency(self, c, CenterFreq):
        dev = self.selectedDevice(c)
        yield dev.write(':Alyzr(0):FFT:CenterFreq %s Hz' %(CenterFreq))
        
    @setting(18, 'Reset_Averaging', returns = '')
    def Reset_Averaging(self, c):
        """
        Starts averaging
        """
        dev = self.selectedDevice(c)
        yield dev.write(':Alyzr(0):FFT:ResetAvg')
    
    @setting(19, 'If_Average_Done', returns = 'i')
    def If_Average_Done(self, c):
        '''
        Queries whether the average is done.
        '''
        dev = self.selectedDevice(c)
        done = yield dev.query(':Alyzr(0):FFT:AvgDone?')   
        returnValue(int(done))

    @setting(20, 'Get_XY_Values', unitX = 's: unit of X axis', unitY = 's: unit of Y axis', returns = '**v[]')
    def Get_XY_Values(self, c, unitX = 'Hz', unitY = 'V/rtHz'):
        '''
        Returns X and Y values on the graph.
        '''
        dev = self.selectedDevice(c)
        number_of_data = yield dev.query(':Displays:Graph(%s):Trace(%s):GetN?' %(self.graphID, self.traceID))
        X = yield dev.query(':Displays:Graph(%s):Trace(%s):GetXArray? %s' %(self.graphID, self.traceID, unitX))
        Y = yield dev.query(':Displays:Graph(%s):Trace(%s):GetYArray? %s' %(self.graphID, self.traceID, unitY))
        XVal = [float(i.replace('"', '').replace('e', 'E')) for i in X.split(",")]
        YVal = [float(i.replace('"', '').replace('e', 'E')) for i in Y.split(",")]
        returnValue([XVal,YVal])
    
    @setting(21, 'Set_FFT_Average_Type', AverageType = 'i', returns = '')
    def Set_Average_Type(self, c, AverageType):
        '''
        Sets the Average Type of FFT Analyzer: {agvNone=0 | avgFixedLength=1 | avgContinuous=2}
        '''
        dev = self.selectedDevice(c)
        yield dev.write(':Alyzr(0):FFT:Averaging %s' %(AverageType))
        
    @setting(22, 'Set_FFT_Average_Num', AverageNum = 'i', returns = '')
    def Set_FFT_Average_Num(self, c, AverageNum):
        '''
        Sets the Average Number of FFT Analyzer
        '''
        dev = self.selectedDevice(c)
        yield dev.write(':Alyzr(0):FFT:NumAverages %s' %(AverageNum))
        
    @setting(23, 'Set_SW_Amplitude', SWAmplitude = 'v: amplitude in unit V (peak to peak)', returns = '')
    def Set_SW_Amplitude(self, c, SWAmplitude):
        '''
        Sets the Amplitude of square wave in the unit of Volt
        '''
        dev = self.selectedDevice(c)
        yield dev.write(':AnlgGen:Ch(0):Square(%s):Amp %s VP' %(self.chanID, SWAmplitude))
        yield dev.write(':AnlgGen:Ch(0):Square(%s):On 1' %(self.chanID))
        
    @setting(24, 'Set_SW_Frequency', SWFrequency = 'v: frequency in unit Hz', returns = '')
    def Set_SW_Frequency(self, c, SWFrequency):
        '''
        Sets the Frequency of the square wave in the unit of Hz
        '''
        dev = self.selectedDevice(c)
        yield dev.write(':AnlgGen:Ch(0):Square(%s):Freq %s Hz' %(self.chanID, SWFrequency))
        yield dev.write(':AnlgGen:Ch(0):Square(%s):On 1' %(self.chanID))
        
    @setting(25, 'SW_OnOff', OnOff = 'i', returns = '')
    def SW_OnOff(self, c, OnOff):
        '''
        Turns on(1) or off(0) the Squarewave output for ChA
        '''
        dev = self.selectedDevice(c)
        yield dev.write(':AnlgGen:Ch(0):On %s' %(OnOff))
    
    
        
__server__ = SR1()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
