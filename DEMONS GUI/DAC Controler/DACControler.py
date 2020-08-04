from __future__ import division
import sys
import os
import twisted
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
from PyQt5 import Qt, QtGui, QtCore, uic
import numpy as np
#import exceptions
import time
import threading
import copy
from scipy.signal import detrend
#importing a bunch of stuff


path = os.path.dirname(os.path.realpath(__file__))
ControlerWindowUI, QtBaseClass = uic.loadUiType(os.path.join(path, "DACControlerWindow.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

#Not required, but strongly recommended functions used to format numbers in a particular way.
#sys.path.append(sys.path[0]+'\Resources')
from DEMONSFormat import *

class Window(QtGui.QMainWindow, ControlerWindowUI):

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.serversList = { #Dictionary including toplevel server received from labrad connect
            'DACADC': False
        }

        self.DeviceList = {}#self.DeviceList['Device Name'][Device Property]

        self.DeviceList['DataAquisition_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_DAQ_SelectServer,
            'ComboBoxDevice': self.comboBox_DAQ_SelectDevice,
            'ServerIndicator': self.pushButton_DAQ_ServerIndicator,
            'DeviceIndicator': self.pushButton_DAQ_DeviceIndicator,            
            'ServerNeeded': ['DACADC'],
        }

        self.targetnumber = {
            'Output1': 0.0,
            'Output2': 0.0,
        }

        self.lineEdit = {
            'Output1': self.lineEdit_TargetNumber_1,
            'Output2': self.lineEdit_TargetNumber_2,
        }

        for key in self.lineEdit:
            if not isinstance(self.targetnumber[key], str):
                UpdateLineEdit_Bound(self.targetnumber, key, self.lineEdit)

        self.DetermineEnableConditions()

        self.comboBox_DAQ_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'DataAquisition_Device', self.serversList, str(self.DeviceList['DataAquisition_Device']['ComboBoxServer'].currentText())))
        self.comboBox_DAQ_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'DataAquisition_Device', str(self.DeviceList['DataAquisition_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_TargetNumber_1.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.targetnumber, 'Output1', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_TargetNumber_2.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.targetnumber, 'Output2', self.lineEdit, [-10.0, 10.0]))

        self.pushButton_SET_1.clicked.connect(lambda: Set_DAC(self.DeviceList['DataAquisition_Device']['DeviceObject'], 0, self.targetnumber['Output1']))
        self.pushButton_SET_2.clicked.connect(lambda: Set_DAC(self.DeviceList['DataAquisition_Device']['DeviceObject'], 1, self.targetnumber['Output2']))

        self.pushButton_Read_1.clicked.connect(lambda: Read_ADC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 0, self.label_ADC_1))
        self.pushButton_Read_2.clicked.connect(lambda: Read_ADC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 1, self.label_ADC_2))
        self.pushButton_Read_3.clicked.connect(lambda: Read_ADC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 2, self.label_ADC_3))
        self.pushButton_Read_4.clicked.connect(lambda: Read_ADC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 3, self.label_ADC_4))

        self.pushButton_ReadAll.clicked.connect(lambda: self.ReadAll())
    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.pushButton_SET_1: not self.DeviceList['DataAquisition_Device']['DeviceObject'] == False,
            self.pushButton_SET_2: not self.DeviceList['DataAquisition_Device']['DeviceObject'] == False,
            self.pushButton_Read_1: not self.DeviceList['DataAquisition_Device']['DeviceObject'] == False,
            self.pushButton_Read_2: not self.DeviceList['DataAquisition_Device']['DeviceObject'] == False,
            self.pushButton_Read_3: not self.DeviceList['DataAquisition_Device']['DeviceObject'] == False,
            self.pushButton_Read_4: not self.DeviceList['DataAquisition_Device']['DeviceObject'] == False,
        }

    def connectServer(self, key, server):
        try:
            self.serversList[str(key)] = server
            self.refreshServerIndicator()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
            print('DACControler')
    def disconnectServer(self, ServerName):
        try:
            self.serversList[str(ServerName)] = False

            for key, DevicePropertyList in self.DeviceList.items():
                if str(ServerName) == str(DevicePropertyList['ComboBoxServer'].currentText()):
                    DevicePropertyList['ServerObject'] = False
                    DevicePropertyList['DeviceObject'] = False
            self.refreshServerIndicator()
            self.Refreshinterface()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def refreshServerIndicator(self):
        try:
            optional = []#This optional will reconstruct combobox multiple time when you disconnect/connect server individually
            flag = True
            for key in self.serversList:
                if self.serversList[str(key)] == False and not str(key) in optional:
                    flag = False
                    
            if flag:
                setIndicator(self.pushButton_Servers, 'rgb(0, 170, 0)')

                for key, DevicePropertyList in self.DeviceList.items():#Reconstruct all combobox when all servers are connected
                    ReconstructComboBox(DevicePropertyList['ComboBoxServer'], DevicePropertyList['ServerNeeded'])

                self.Refreshinterface()
            else:
                setIndicator(self.pushButton_Servers, 'rgb(161, 0, 0)')
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)

        for key, DevicePropertyList in self.DeviceList.items():
            RefreshIndicator(DevicePropertyList['ServerIndicator'], DevicePropertyList['ServerObject'])
            RefreshIndicator(DevicePropertyList['DeviceIndicator'], DevicePropertyList['DeviceObject'])
            
    def moveDefault(self):
        self.move(10,170)
        
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
    
    def ReadAll(self):
        Read_ADC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 0, self.label_ADC_1)
        Read_ADC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 1, self.label_ADC_2)
        Read_ADC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 2, self.label_ADC_3)
        Read_ADC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 3, self.label_ADC_4)

        Read_DAC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 0, self.label_DAC0)
        Read_DAC_SetLabel(self.DeviceList['DataAquisition_Device']['DeviceObject'], 1, self.label_DAC1)

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))
