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
Ui_AMISetting, QtBaseClass = uic.loadUiType(os.path.join(path , "MagnetInstrumentSetting.ui"))

class AMISetting(QtGui.QMainWindow, Ui_AMISetting):
    complete = QtCore.pyqtSignal()

    def __init__(self, reactor, parent = None):
        super(AMISetting, self).__init__(parent)
        from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg, s

        self.reactor = reactor
        self.setupUi(self)
        
        self.Servers = {}
        self.Devices = {}

        self.parent = parent

        self.DeviceList = {}

        self.DeviceList['AMI430'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_AMI_SelectServer,
            'ComboBoxDevice': self.comboBox_AMI_SelectDevice,
            'ServerIndicator': self.pushButton_AMI_ServerIndicator,
            'DeviceIndicator': self.pushButton_AMI_DeviceIndicator,
            'ServerNeeded': ['AMI430_X','AMI430_Y','AMI430_Z'],
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
            'Name': 'AMI Default',
            'InstrumentType': 'AMI430',
            'DeviceObject': None,
            'Device': None,
            'Measurement': None, # input or output
            'RampRate': None,
            'MaxField': None,
            'ReadFn': ReadAMIInstrumentSetting,
            'WriteFn': WriteAMIInstrumentSetting

        }
        self.lineEdit = {

            'Name': self.lineEdit_Name,
            'RampRate': self.lineEdit_RampRate,
            'MaxField': self.lineEdit_MaxField
        }
        ##Input 
        self.DetermineEnableConditions()

        self.comboBox_AMI_SelectServer.currentIndexChanged.connect(lambda: self.selectServer(self.InstrumentDict,str(self.DeviceList['AMI430']['ComboBoxServer'].currentText()),self.DeviceList['AMI430']))
        self.comboBox_AMI_SelectDevice.currentIndexChanged.connect(lambda: self.selectDevice(self.DeviceList,'AMI430',self.comboBox_AMI_SelectDevice.currentText()))
        

        #self.comboBox_LI_SelectDevice.currentIndexChanged.connect(lambda: self.sel())

        self.lineEdit_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.InstrumentDict,'Name',self.lineEdit))
        self.comboBox_Measurement.currentIndexChanged.connect(lambda: SetComboBox_Parameter(self.InstrumentDict,'Measurement',self.comboBox_Measurement.currentText(),refreshFunc=self.Refreshinterface))
        self.lineEdit_RampRate.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.InstrumentDict,'RampRate',self.lineEdit,[0.0,30.0]))
        self.lineEdit_MaxField.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.InstrumentDict,'MaxField',self.lineEdit,[-10.0,10.0]))

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
                    if DeviceName == 'AMI430':
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
            self.lineEdit_RampRate: (self.InstrumentDict['Measurement'] == 'Output'),
            self.lineEdit_MaxField: (self.InstrumentDict['Measurement'] == 'Output'),
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
            'Name': 'AMI Default',
            'InstrumentType': 'AMI430',
            'DeviceObject': None,
            'Device': None,
            'Measurement': None, # input or output
            'TempCh1': None,
            'TempCh2': None,
            'OutputLoop': None,
            'FeedbackCh': None,
            'HeaterRange': None,
            'RampRate': None,
            'ReadFn': ReadAMIInstrumentSetting,
            'WriteFn': WriteAMIInstrumentSetting
        }
        self.lineEdit_Name.setText('')
        self.lineEdit_RampRate.setText('')
        self.comboBox_Measurement.setCurrentText('')
        self.lineEdit_MaxField.setText('')
        self.comboBox_AMI_SelectDevice.setCurrentText('Offline')
    def moveDefault(self):
        self.move(400,100)

@inlineCallbacks
def ReadAMIInstrumentSetting(instrumentDict):
    magnet = instrumentDict['DeviceObject']
    field = yield magnet.get_field_mag()
    returnValue([field])

@inlineCallbacks
def WriteAMIInstrumentSetting(instrumentDict,magnet_setpt):
    magnet = instrumentDict['DeviceObject']
    ramprate = instrumentDict['RampRate']
    maxfield = instrumentDict['MaxField']
    inputs = {'Target': magnet_setpt,'Max_Field': maxfield,'FieldRate':ramprate,'Max_Ramp_Rate':ramprate}
    yield Set_AMI(magnet, inputs)
    yield Ramp_AMI(magnet)
    state = yield magnet.state()
    while state == 1:
        state = yield magnet.state()
    if state == 2 or state == 3 or state == 8:
        field = yield magnet.get_field_mag()
        returnValue([field])
    else:
        returnValue([-99999])
    