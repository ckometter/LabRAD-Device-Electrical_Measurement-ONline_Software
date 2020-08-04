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
Ui_DACADCSetting, QtBaseClass = uic.loadUiType(os.path.join(path , "DACADCInstrumentSetting.ui"))

class DACADCSetting(QtGui.QMainWindow, Ui_DACADCSetting):
    complete = QtCore.pyqtSignal()

    def __init__(self, reactor, parent = None):
        super(DACADCSetting, self).__init__(parent)
        from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg, s

        self.reactor = reactor
        self.setupUi(self)
        
        self.Servers = {}
        self.Devices = {}

        self.parent = parent

        self.DeviceList = {}

        self.DeviceList['DACADC'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_DACADC_SelectServer,
            'ComboBoxDevice': self.comboBox_DACADC_SelectDevice,
            'ServerIndicator': self.pushButton_DACADC_ServerIndicator,
            'DeviceIndicator': self.pushButton_DACADC_DeviceIndicator,
            'ServerNeeded': ['DACADC'],
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
            'Name': 'DACADC Default',
            'InstrumentType': 'DAC-ADC',
            'DeviceObject': None,
            'Device': None,
            'Measurement': None,
            'DAC Output': None,
            'ADC Input': None,
            'ReadFn': ReadDACADCInstrumentSetting,
            'WriteFn': WriteDACADCInstrumentSetting

        }

        self.lineEdit = {
            'Name': self.lineEdit_Name,
        }
        ##Input 
        self.DetermineEnableConditions()

        
        self.comboBox_DACADC_SelectServer.currentIndexChanged.connect(lambda: self.selectServer(self.InstrumentDict,str(self.DeviceList['DACADC']['ComboBoxServer'].currentText()),self.DeviceList['DACADC']))
        self.comboBox_DACADC_SelectDevice.currentIndexChanged.connect(lambda: self.selectDevice(self.DeviceList,'DACADC',self.comboBox_DACADC_SelectDevice.currentText()))

        self.lineEdit_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.InstrumentDict,'Name',self.lineEdit))
        
        self.comboBox_Measurement.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'Measurement',self.comboBox_Measurement.currentText(),refreshFunc=self.Refreshinterface))
        self.comboBox_ADCInput.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'ADC Input',self.comboBox_ADCInput.currentText()))
        self.comboBox_DACOutput.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict, 'DAC Output', self.comboBox_DACOutput.currentText()))

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
                    if DeviceName == 'DACADC':
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
            self.comboBox_DACADC_SelectServer: True,
            self.comboBox_DACADC_SelectDevice: True,
            self.comboBox_ADCInput: (self.InstrumentDict['Measurement'] == 'Input'),
            self.comboBox_DACOutput: self.InstrumentDict['Measurement'] == 'Output', 
        }

    def done(self):
        if self.InstrumentDict['Measurement'] == 'Input':
            self.InstrumentDict['DAC Output'] = None
        elif self.InstrumentDict['Measurement'] == 'Output':
            self.InstrumentDict['ADC Input'] = None
        self.complete.emit()
        self.close()

    def closeWindow(self):
        self.close()

    def initialize(self,input_dictionary):
        self.lineEdit_Name.setText(input_dictionary['Name'])
        self.comboBox_Measurement.setCurrentText(input_dictionary['Measurement'])
        if input_dictionary['Measurement'] == 'Input':
            self.comboBox_ADCInput.setCurrentText(input_dictionary['ADC Input'])
        elif input_dictionary['Measurement'] == 'Output':
            self.comboBox_DACOutput.setCurrentText(input_dictionary['DAC Output'])
        self.comboBox_DACADC_SelectDevice.setCurrentText(input_dictionary['Device'])

    def clearInfo(self):

        self.InstrumentDict = {
            'Name': 'DACADC Default',
            'InstrumentType': 'DAC-ADC',
            'DeviceObject': None,
            'Device': None,
            'Measurement': None,
            'DAC Output': None,
            'ADC Input': None,
            'ReadFn': ReadDACADCInstrumentSetting,
            'WriteFn': WriteDACADCInstrumentSetting
        }
        self.lineEdit_Name.setText('DACADC Default')
        self.comboBox_DACOutput.setCurrentText('')
        self.comboBox_Measurement.setCurrentText('')
        self.comboBox_ADCInput.setCurrentText('')
        self.comboBox_DACADC_SelectDevice.setCurrentText('Offline')
    def moveDefault(self):
        self.move(400,100)
