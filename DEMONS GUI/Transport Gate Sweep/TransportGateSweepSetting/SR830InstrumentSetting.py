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
Ui_SR830Setting, QtBaseClass = uic.loadUiType(os.path.join(path , "SR830InstrumentSetting.ui"))

class SR830Setting(QtGui.QMainWindow, Ui_SR830Setting):
    complete = QtCore.pyqtSignal()

    def __init__(self, reactor, parent = None):
        super(SR830Setting, self).__init__(parent)
        from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg, s,A 

        self.reactor = reactor
        self.setupUi(self)
        
        self.Servers = {}
        self.Devices = {}

        self.parent = parent

        self.DeviceList = {}

        self.DeviceList['SR830'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_LI_SelectDevice,
            'ServerIndicator': self.pushButton_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_LI_DeviceIndicator,
            'ServerNeeded': ['SR830_0','SR830_1'],
        }

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
            's': s,
            'A': A
            
        }

        self.InstrumentDict = {
            'Name': 'Lockin Default',
            'InstrumentType': 'SR830',
            'DeviceObject': None,
            'Device': None,
            'Excitation': None,
            'Frequency': None,
            'Time Constant': None,
            'Sensitivity': None,
            'LIReading': 'X/Y', #'X/Y' or 'R/T'
            'Measurement': 'SR830', #'SR830' or 'DACADC'
            'DACADCDevice': None, #these are used if we measure using the DACADC
            'DACADCDeviceObject': None, 
            'DACADCChannelX': None,
            'DACADCChannelY': None,
            'ReadFn': ReadSR830InstrumentSetting,

        }
        self.lineEdit = {

            'Name': self.lineEdit_Name,
            'Excitation': self.lineEdit_Excitation,
            'Time Constant': self.lineEdit_Timeconstant,
            'Sensitivity': self.lineEdit_Sensitivity,
            'Frequency': self.lineEdit_Frequency,
        }
        ##Input 
        self.DetermineEnableConditions()

        self.comboBox_LI_SelectServer.currentIndexChanged.connect(lambda: self.selectServer(self.InstrumentDict,str(self.DeviceList['SR830']['ComboBoxServer'].currentText()),self.DeviceList['SR830']))
        self.comboBox_LI_SelectDevice.currentIndexChanged.connect(lambda: self.selectDevice(self.DeviceList,'SR830',self.comboBox_LI_SelectDevice.currentText()))
        
        self.comboBox_DACADC_SelectServer.currentIndexChanged.connect(lambda: self.selectServer(self.InstrumentDict,str(self.DeviceList['DACADC']['ComboBoxServer'].currentText()),self.DeviceList['DACADC']))
        self.comboBox_DACADC_SelectDevice.currentIndexChanged.connect(lambda: self.selectDevice(self.DeviceList,'DACADC',self.comboBox_DACADC_SelectDevice.currentText()))


        #self.comboBox_LI_SelectDevice.currentIndexChanged.connect(lambda: self.sel())

        self.lineEdit_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.InstrumentDict,'Name',self.lineEdit))
        
        self.lineEdit_Excitation.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.InstrumentDict, 'Excitation', self.lineEdit,[0.0,5.0]))
        self.pushButton_ExcitationRead.clicked.connect(lambda: ReadEdit_Parameter(self.InstrumentDict['DeviceObject'].sine_out_amplitude, self.InstrumentDict, 'Excitation', self.lineEdit['Excitation'],'V'))
        self.pushButton_ExcitationSet.clicked.connect(lambda: SetEdit_Parameter(self.InstrumentDict['DeviceObject'].sine_out_amplitude, self.InstrumentDict, 'Excitation', self.lineEdit['Excitation'],self.units['V']))#Send to Voltage Lock in

        self.lineEdit_Frequency.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.InstrumentDict, 'Frequency', self.lineEdit))
        self.pushButton_FrequencyRead.clicked.connect(lambda: ReadEdit_Parameter(self.InstrumentDict['DeviceObject'].frequency, self.InstrumentDict, 'Frequency', self.lineEdit['Frequency'], 'Hz'))
        self.pushButton_FrequencySet.clicked.connect(lambda: SetEdit_Parameter(self.InstrumentDict['DeviceObject'].frequency, self.InstrumentDict, 'Frequency', self.lineEdit['Frequency'],self.units['Hz']))#Send to Voltage Lock in
        
        self.lineEdit_Timeconstant.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.InstrumentDict, 'Time Constant', self.lineEdit))
        self.pushButton_Timeconstant_Read.clicked.connect(lambda: ReadEdit_Parameter(self.InstrumentDict['DeviceObject'].time_constant, self.InstrumentDict, 'Time Constant', self.lineEdit['Time Constant'],'s'))
        self.pushButton_Timeconstant_Incr.clicked.connect(lambda: SetEdit_Parameter(self.InstrumentDict['DeviceObject'].time_constant_up, self.InstrumentDict, 'Time Constant', self.lineEdit['Time Constant'],self.units['s']))#Send to Voltage Lock in
        self.pushButton_Timeconstant_Decr.clicked.connect(lambda: SetEdit_Parameter(self.InstrumentDict['DeviceObject'].time_constant_down, self.InstrumentDict, 'Time Constant', self.lineEdit['Time Constant'],self.units['s']))#Send to Voltage Lock in
        
        self.lineEdit_Sensitivity.editingFinished.connect(lambda: ReadEdit_Parameter_LI_Sens(self.InstrumentDict['DeviceObject'].sensitivity, self.InstrumentDict, 'Sensitivity', self.lineEdit['Sensitivity'],self.InstrumentDict['DeviceObject']))
        self.pushButton_Sensitivity_Read.clicked.connect(lambda: ReadEdit_Parameter_LI_Sens(self.InstrumentDict['DeviceObject'].sensitivity, self.InstrumentDict, 'Sensitivity', self.lineEdit['Sensitivity'],self.InstrumentDict['DeviceObject']))
        self.pushButton_Sensitivity_Incr.clicked.connect(lambda: SetEdit_Parameter_LI_Sens(self.InstrumentDict['DeviceObject'].sensitivity_up, self.InstrumentDict, 'Sensitivity', self.lineEdit['Sensitivity'],self.InstrumentDict['DeviceObject'],self.units['V'],self.units['A']))
        self.pushButton_Sensitivity_Decr.clicked.connect(lambda: SetEdit_Parameter_LI_Sens(self.InstrumentDict['DeviceObject'].sensitivity_down, self.InstrumentDict, 'Sensitivity', self.lineEdit['Sensitivity'],self.InstrumentDict['DeviceObject'],self.units['V'],self.units['A']))#Send to Voltage Lock in

        self.comboBox_LIReading.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'LIReading',self.comboBox_LIReading.currentText()))

        self.comboBox_ChooseMeasurement.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'Measurement',self.comboBox_ChooseMeasurement.currentText()))
        self.comboBox_ADC_ChX.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'DACADCChannelX',self.comboBox_ADC_ChX.currentText()))
        self.comboBox_ADC_ChY.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'DACADCChannelY',self.comboBox_ADC_ChY.currentText()))

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
                    if DeviceName == 'SR830':
                        self.InstrumentDict['DeviceObject'] = DeviceList[str(DeviceName)]['DeviceObject']
                        self.InstrumentDict['Device'] = str(target)
                    else:
                        self.InstrumentDict['DACADCDeviceObject'] = DeviceList[str(DeviceName)]['DeviceObject']
                        self.InstrumentDict['DACADCDevice'] = str(target)
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
            self.comboBox_LI_SelectServer: True,
            self.comboBox_LI_SelectDevice: True,
        }

    def done(self):
        if self.InstrumentDict['Measurement'] != 'DACADC':
            self.InstrumentDict['DACADCDevice'] = None
            self.InstrumentDict['DACADCDeviceObject'] = None
            self.InstrumentDict['DACADCChannelX'] = None
            self.InstrumentDict['DACADCChannelY'] = None
        self.complete.emit()
        self.close()

    def closeWindow(self):
        self.close()

    def initialize(self,input_dictionary):
        self.lineEdit_Name.setText(input_dictionary['Name'])
        self.lineEdit_Excitation.setText(str(input_dictionary['Excitation']))
        self.lineEdit_Frequency.setText(str(input_dictionary['Frequency']))
        self.lineEdit_Sensitivity.setText(str(input_dictionary['Sensitivity']))
        self.lineEdit_Timeconstant.setText(str(input_dictionary['Time Constant']))
        self.comboBox_ChooseMeasurement.setCurrentText(input_dictionary['Measurement'])
        self.comboBox_LI_SelectDevice.setCurrentText(input_dictionary['Device'])
        if input_dictionary['Measurement'] == 'DACADC':
            self.comboBox_ADC_ChY.setCurrentText(input_dictionary['DACADCChannelY'])
            self.comboBox_ADC_ChX.setCurrentText(input_dictionary['DACADCChannelX'])
            self.comboBox_DACADC_SelectDevice.setCurrentText(input_dictionary['DACADCDevice'])

    def clearInfo(self):
        self.InstrumentDict = {
            'Name': 'Lockin Default',
            'InstrumentType': 'SR830',
            'DeviceObject': None,
            'Device': None,
            'Excitation': None,
            'Frequency': None,
            'Time Constant': None,
            'Sensitivity': None,
            'LIReading': 'X/Y',
            'Measurement': 'SR830', #'LI' or 'DACADC'
            'DACADCDevice': None, #these are used if we measure using the DACADC
            'DACADCDeviceObject': None, 
            'DACADCChannelX': None,
            'DACADCChannelY': None,
            'ReadFn': ReadSR830InstrumentSetting,
        }
        self.lineEdit_Name.setText('')
        self.lineEdit_Excitation.setText('')
        self.lineEdit_Frequency.setText('')
        self.lineEdit_Sensitivity.setText('')
        self.lineEdit_Timeconstant.setText('')
        self.comboBox_ChooseMeasurement.setCurrentText('None')
        self.comboBox_LI_SelectDevice.setCurrentText('Offline')
        self.comboBox_ADC_ChY.setCurrentText('')
        self.comboBox_ADC_ChX.setCurrentText('')
        self.comboBox_LIReading.setCurrentText('X/Y')
        self.comboBox_DACADC_SelectDevice.setCurrentText('Offline')
    def moveDefault(self):
        self.move(400,100)
