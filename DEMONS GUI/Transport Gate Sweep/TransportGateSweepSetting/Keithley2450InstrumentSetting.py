import sys
import twisted
from PyQt5 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import pyqtgraph as pg
#import exceptions
import time
import threading
import copy

from DEMONSFormat import *

path = os.path.dirname(os.path.realpath(__file__))
Ui_Keithley2450Setting, QtBaseClass = uic.loadUiType(os.path.join(path , "Keithley2450InstrumentSetting.ui"))

class Keithley2450Setting(QtGui.QMainWindow, Ui_Keithley2450Setting):
    complete = QtCore.pyqtSignal()

    def __init__(self, reactor, parent = None):
        super(Keithley2450Setting, self).__init__(parent)
        from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg, s

        self.reactor = reactor
        self.setupUi(self)
        
        self.Servers = {}
        self.Devices = {}

        self.parent = parent

        self.DeviceList = {}

        self.DeviceList['Keithley2450'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Keithley2450_SelectServer,
            'ComboBoxDevice': self.comboBox_Keithley2450_SelectDevice,
            'ServerIndicator': self.pushButton_Keithley2450_ServerIndicator,
            'DeviceIndicator': self.pushButton_Keithley2450_DeviceIndicator,
            'ServerNeeded': ['Keithley2450'],
        }


        self.units = {
            'Hz': Hz,
            'V': V,
            'mV': mV,
            'us': us,
            'ns': ns,
            'GHz': GHz,
            'MHz': MHz,
            's': s
            
        }

        self.InstrumentDict = {
            'Name': 'Keithley2450 Default',
            'InstrumentType': 'Keithley2450',
            'DeviceObject': None,
            'Device': None,
            'Measurement': None,
            'Mode': None,
            'ReadFn': ReadKeithley2450InstrumentSetting,
            'WriteFn': WriteKeithley2450InstrumentSetting

        }

        self.lineEdit = {
            'Name': self.lineEdit_Name,
        }
        ##Input 
        self.DetermineEnableConditions()

        
        self.comboBox_Keithley2450_SelectServer.currentIndexChanged.connect(lambda: self.selectServer(self.InstrumentDict,str(self.DeviceList['Keithley2450']['ComboBoxServer'].currentText()),self.DeviceList['Keithley2450']))
        self.comboBox_Keithley2450_SelectDevice.currentIndexChanged.connect(lambda: self.selectDevice(self.DeviceList,'Keithley2450',self.comboBox_Keithley2450_SelectDevice.currentText()))

        self.lineEdit_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.InstrumentDict,'Name',self.lineEdit))
        
        self.comboBox_Measurement.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'Measurement',self.comboBox_Measurement.currentText(),refreshFunc=self.Refreshinterface))
        self.comboBox_Mode.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'Mode',self.comboBox_Mode.currentText()))

        self.pushButton_Done.clicked.connect(lambda: self.done())
        self.pushButton_Cancel.clicked.connect(lambda: self.closeWindow())

    def selectServer(self,instr_dict, servername,devlist):
        if servername != '':
            devlist['ServerObject'] = self.Servers[servername]
            #if servername == 'SR830':
            #    instr_dict['Server'] = self.Servers[servername]
            #elif servername == 'DACADC':
            #    instr_dict['DACADCServer'] = self.Servers[servername]
            RedefineComboBox(devlist['ComboBoxDevice'],self.Servers[servername])
            self.Refreshinterface()

    @inlineCallbacks
    def selectDevice(self,DeviceList,DeviceName,target):
        try:
            if str(target) != 'Offline' and DeviceList[DeviceName]['ServerObject'] != False and str(target) != '':#target can be blank when reconstruct the combobox
                try:
                    DeviceList[str(DeviceName)]['DeviceObject'] = DeviceList[str(DeviceName)]['ServerObject']
                    yield DeviceList[str(DeviceName)]['DeviceObject'].select_device(str(target))
                    if DeviceName == 'Keithley2450':
                        self.InstrumentDict['DeviceObject'] = DeviceList[str(DeviceName)]['DeviceObject']
                        self.InstrumentDict['Device'] = str(target)
                except Exception as inst:
                    print('Connection to ' +str(DeviceName)+  ' failed: ', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
                    DeviceList[str(DeviceName)]['DeviceObject'] = False
            else:
                DeviceList[str(DeviceName)]['DeviceObject'] = False
            RefreshIndicator(DeviceList[str(DeviceName)]['DeviceIndicator'], DeviceList[str(DeviceName)]['DeviceObject'])
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
        self.Refreshinterface()

    def refreshServerIndicator(self):
        flag = True
        for key in self.Servers:
            if self.Servers[str(key)] == False:
                flag = False
        if flag:
            setIndicator(self.pushButton_Servers,'rgb(0,170,0)')
            for key, devlist in self.DeviceList.items():
                ReconstructComboBox(devlist['ComboBoxServer'],devlist['ServerNeeded'])
            self.Refreshinterface()
        else:
            setIndicator(self.pushButton_Servers,'rgb(161,0,0)')

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)
        for key, dlist in self.DeviceList.items():
            RefreshIndicator(dlist['ServerIndicator'],dlist['ServerObject'])
            RefreshIndicator(dlist['DeviceIndicator'],dlist['DeviceObject'])

    def DetermineEnableConditions(self):
        self.ButtonsCondition = {
            self.comboBox_Keithley2450_SelectServer: True,
            self.comboBox_Keithley2450_SelectDevice: True,
            #self.comboBox_ADCInput: (self.InstrumentDict['Measurement'] == 'Input'),
            #self.comboBox_DACOutput: self.InstrumentDict['Measurement'] == 'Output', 
        }

    def done(self):
        if self.InstrumentDict['Measurement'] == 'Output':
            if self.InstrumentDict['Mode'] == 'Current':
                self.InstrumentDict['DeviceObject'].source_current()
                self.InstrumentDict['DeviceObject'].set_source_current(0)
            elif self.InstrumentDict['Mode'] == 'Voltage':
                self.InstrumentDict['DeviceObject'].source_voltage()
                self.InstrumentDict['DeviceObject'].set_source_voltage(0)
            self.InstrumentDict['DeviceObject'].output_on()
        self.complete.emit()
        self.close()

    def closeWindow(self):
        self.close()

    def initialize(self,input_dictionary):
        self.lineEdit_Name.setText(input_dictionary['Name'])
        self.comboBox_Measurement.setCurrentText(input_dictionary['Measurement'])
        self.comboBox_Mode.setCurrentText(input_dictionary['Mode'])
        self.comboBox_Keithley2450_SelectDevice.setCurrentText(input_dictionary['Device'])

    def clearInfo(self):

        self.InstrumentDict = {
            'Name': 'Keithley2450 Default',
            'InstrumentType': 'Keithley2450',
            'DeviceObject': None,
            'Device': None,
            'Measurement': None,
            'Mode': None,
            'ReadFn': ReadKeithley2450InstrumentSetting,
            'WriteFn': WriteKeithley2450InstrumentSetting

        }
        self.lineEdit_Name.setText('Keihley2450 Default')
        self.comboBox_Mode.setCurrentText('')
        self.comboBox_Measurement.setCurrentText('')
        self.comboBox_Keithley2450_SelectDevice.setCurrentText('Offline')

    def moveDefault(self):
        self.move(400,100)

@inlineCallbacks
def ReadKeithley2450InstrumentSetting(instrumentDict):
    meas_type = instrumentDict['Measurement'] #this should be 'Input' or 'Output'
    ke = instrumentDict['DeviceObject']
    mode = instrumentDict['Mode']
    if mode == 'Current':
        value = yield ke.measure_current()
        returnValue([value])
    elif mode == 'Voltage':
        value = yield ke.measure_voltage()
        returnValue([value])

@inlineCallbacks
def WriteKeithley2450InstrumentSetting(instrumentDict,value): #port should input "Top" or "Bottom"
    ke = instrumentDict['DeviceObject']
    if instrumentDict['Measurement'] == 'Output':
        if instrumentDict['Mode'] == 'Voltage':
            yield ke.set_source_voltage(value)
        elif instrumentDict['Mode'] == 'Current':
            yield ke.set_source_current(value)


