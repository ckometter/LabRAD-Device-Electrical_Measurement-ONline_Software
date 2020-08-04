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
Ui_LakeshoreSetting, QtBaseClass = uic.loadUiType(os.path.join(path , "LakeshoreInstrumentSetting.ui"))

class LakeshoreSetting(QtGui.QMainWindow, Ui_LakeshoreSetting):
    complete = QtCore.pyqtSignal()

    def __init__(self, reactor, parent = None):
        super(LakeshoreSetting, self).__init__(parent)
        from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg, s

        self.reactor = reactor
        self.setupUi(self)
        
        self.Servers = {}
        self.Devices = {}

        self.parent = parent

        self.DeviceList = {}

        self.DeviceList['Lakeshore'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Lakeshore_SelectServer,
            'ComboBoxDevice': self.comboBox_Lakeshore_SelectDevice,
            'ServerIndicator': self.pushButton_Lakeshore_ServerIndicator,
            'DeviceIndicator': self.pushButton_Lakeshore_DeviceIndicator,
            'ServerNeeded': ['Lakeshore'],
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
            'Name': 'Lakeshore Default',
            'InstrumentType': 'Lakeshore',
            'DeviceObject': None,
            'Device': None,
            'Measurement': None, # input or output
            'TempCh1': None,
            'TempCh2': None,
            'OutputLoop': None,
            'FeedbackCh': None,
            'HeaterRange': None,
            'RampRate': None,
            'ReadFn': ReadLakeshoreInstrumentSetting,
            'WriteFn': WriteLakeshoreInstrumentSetting

        }
        self.lineEdit = {

            'Name': self.lineEdit_Name,
            'RampRate': self.lineEdit_RampRate,
        }
        ##Input 
        self.DetermineEnableConditions()

        self.comboBox_Lakeshore_SelectServer.currentIndexChanged.connect(lambda: self.selectServer(self.InstrumentDict,str(self.DeviceList['Lakeshore']['ComboBoxServer'].currentText()),self.DeviceList['Lakeshore']))
        self.comboBox_Lakeshore_SelectDevice.currentIndexChanged.connect(lambda: self.selectDevice(self.DeviceList,'Lakeshore',self.comboBox_Lakeshore_SelectDevice.currentText()))
        

        #self.comboBox_LI_SelectDevice.currentIndexChanged.connect(lambda: self.sel())

        self.lineEdit_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.InstrumentDict,'Name',self.lineEdit))
        self.comboBox_Measurement.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'Measurement',self.comboBox_Measurement.currentText(),refreshFunc=self.Refreshinterface))
        self.comboBox_TempCh1.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'TempCh1',self.comboBox_TempCh1.currentText()))
        self.comboBox_TempCh2.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'TempCh2',self.comboBox_TempCh2.currentText()))
        self.comboBox_OutputLoop.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'OutputLoop', self.comboBox_OutputLoop.currentText()))
        self.comboBox_FeedbackCh.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'FeedbackCh', self.comboBox_FeedbackCh.currentText()))

        self.comboBox_HeaterRange.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'Heater Range', self.comboBox_HeaterRange.currentText()))
        self.lineEdit_RampRate.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.InstrumentDict,'RampRate',self.lineEdit,[0.0,30.0]))

        self.pushButton_Done.clicked.connect(lambda: self.done())
        self.pushButton_Cancel.clicked.connect(lambda: self.closeWindow())

    def selectServer(self,instr_dict, servername,devlist):
        if servername != '':
            devlist['ServerObject'] = self.Servers[servername]
            RedefineComboBox(devlist['ComboBoxDevice'],self.Servers[servername])
            self.Refreshinterface()

    @inlineCallbacks
    def selectDevice(self,DeviceList,DeviceName,target):
        try:
            if str(target) != 'Offline' and DeviceList[DeviceName]['ServerObject'] != False and str(target) != '':#target can be blank when reconstruct the combobox
                try:
                    DeviceList[str(DeviceName)]['DeviceObject'] = DeviceList[str(DeviceName)]['ServerObject']
                    yield DeviceList[str(DeviceName)]['DeviceObject'].select_device(str(target))
                    if DeviceName == 'Lakeshore':
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
            self.comboBox_OutputLoop: (self.InstrumentDict['Measurement'] == 'Output'),
            self.comboBox_FeedbackCh: (self.InstrumentDict['Measurement'] == 'Output'),
            self.comboBox_HeaterRange: (self.InstrumentDict['Measurement'] == 'Output'),
            self.lineEdit_RampRate: (self.InstrumentDict['Measurement'] == 'Output'),
        }

    def done(self):
        if self.InstrumentDict['Measurement'] == 'Input':
            self.InstrumentDict['OutputLoop'] = None
            self.InstrumentDict['FeedbackCh'] = None
            self.InstrumentDict['HeaterRange'] = None
            self.InstrumentDict['RampRate'] = None
        self.complete.emit()
        self.close()

    def closeWindow(self):
        self.close()

    def initialize(self,input_dictionary):
        self.lineEdit_Name.setText(input_dictionary['Name'])
        self.comboBox_Measurement.setCurrentText(input_dictionary['Measurement'])
        self.comboBox_Lakeshore_SelectDevice.setCurrentText(input_dictionary['Device'])
        self.comboBox_TempCh1.setCurrentText(input_dictionary['TempCh1'])
        self.comboBox_TempCh2.setCurrentText(input_dictionary['TempCh2'])
        if input_dictionary['Measurement'] == 'Output':
            self.lineEdit_RampRate.setText(input_dictionary['RampRate'])
            self.comboBox_HeaterRange.setCurrentText(input_dictionary['HeaterRange'])
            self.comboBox_OutputLoop.setCurrentText(input_dictionary['OuputLoop'])

    def clearInfo(self):
        self.InstrumentDict = {
            'Name': 'Lakeshore Default',
            'InstrumentType': 'Lakeshore',
            'DeviceObject': None,
            'Device': None,
            'Measurement': None, # input or output
            'TempCh1': None,
            'TempCh2': None,
            'OutputLoop': None,
            'FeedbackCh': None,
            'HeaterRange': None,
            'RampRate': None,
            'ReadFn': ReadLakeshoreInstrumentSetting,
            'WriteFn': WriteLakeshoreInstrumentSetting
        }
        self.lineEdit_Name.setText('')
        self.lineEdit_RampRate.setText('')
        self.comboBox_Measurement.setCurrentText('')
        self.comboBox_TempCh1.setCurrentText('')
        self.comboBox_TempCh2.setCurrentText('')
        self.comboBox_OutputLoop.setCurrentText('')
        self.comboBox_HeaterRange.setCurrentText('')
        self.comboBox_Lakeshore_SelectDevice.setCurrentText('Offline')
    def moveDefault(self):
        self.move(400,100)
