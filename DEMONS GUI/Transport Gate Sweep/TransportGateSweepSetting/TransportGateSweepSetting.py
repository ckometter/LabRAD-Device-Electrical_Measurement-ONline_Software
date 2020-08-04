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
import SR830InstrumentSetting
import DACADCInstrumentSetting
import LakeshoreInstrumentSetting
import MagnetInstrumentSetting
import Keithley2450InstrumentSetting
import CustomVarInstrumentSetting
from DEMONSFormat import *

path = os.path.dirname(os.path.realpath(__file__))
Ui_Setting, QtBaseClass = uic.loadUiType(os.path.join(path , "TransportGateSweepSettingWindow.ui"))

class Setting(QtGui.QMainWindow, Ui_Setting):
    busset = QtCore.pyqtSignal()
    def __init__(self, reactor, parent = None):
        super(Setting, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        
        self.parent = parent

        self.Servers = {}
        self.Devices = {}
        self.bus = {}

        self.SR830_InstrumentSetting = SR830InstrumentSetting.SR830Setting(self.reactor,self)
        self.DACADC_InstrumentSetting = DACADCInstrumentSetting.DACADCSetting(self.reactor, self)
        self.Lakeshore_InstrumentSetting = LakeshoreInstrumentSetting.LakeshoreSetting(self.reactor,self)
        self.Keithley2450_InstrumentSetting = Keithley2450InstrumentSetting.Keithley2450Setting(self.reactor,self)
        self.CustomVar_InstrumentSetting = CustomVarInstrumentSetting.CustomVarSetting(self.reactor,self)
        self.Magnet_InstrumentSetting = MagnetInstrumentSetting.AMISetting(self.reactor,self)
        self.inst_list = ['Lakeshore','SR830','DAC-ADC','AMI430','Keithley2450','CustomVar']

        self.InstrumentList.addItems(self.inst_list)

        self.pushButton_Add.clicked.connect(lambda: self.AddInstrument(self.InstrumentList))
        self.pushButton_Delete.clicked.connect(lambda: self.DeleteInstrument(self.BusList))
        self.pushButton_Edit.clicked.connect(lambda: self.EditInstrument(self.BusList))
        self.BusList.currentItemChanged.connect(lambda: self.printInfo(self.BusList.currentItem(),self.bus))
        self.SR830_InstrumentSetting.complete.connect(lambda: ReadInstrumentSetting(self.bus,self.SR830_InstrumentSetting.InstrumentDict['Name'], self.SR830_InstrumentSetting.InstrumentDict,self.RefreshBus))
        self.DACADC_InstrumentSetting.complete.connect(lambda: ReadInstrumentSetting(self.bus,self.DACADC_InstrumentSetting.InstrumentDict['Name'], self.DACADC_InstrumentSetting.InstrumentDict,self.RefreshBus))
        self.Lakeshore_InstrumentSetting.complete.connect(lambda: ReadInstrumentSetting(self.bus,self.Lakeshore_InstrumentSetting.InstrumentDict['Name'],self.Lakeshore_InstrumentSetting.InstrumentDict,self.RefreshBus))
        self.Magnet_InstrumentSetting.complete.connect(lambda: ReadInstrumentSetting(self.bus,self.Magnet_InstrumentSetting.InstrumentDict['Name'],self.Magnet_InstrumentSetting.InstrumentDict,self.RefreshBus))
        self.Keithley2450_InstrumentSetting.complete.connect(lambda: ReadInstrumentSetting(self.bus,self.Keithley2450_InstrumentSetting.InstrumentDict['Name'],self.Keithley2450_InstrumentSetting.InstrumentDict,self.RefreshBus))
        self.CustomVar_InstrumentSetting.complete.connect(lambda: ReadInstrumentSetting(self.bus,self.CustomVar_InstrumentSetting.InstrumentDict['Name'],self.CustomVar_InstrumentSetting.InstrumentDict,self.RefreshBus))
        self.pushButton_Close.clicked.connect(lambda: self.closeBus())
    
    def AddInstrument(self,instrumentList):
        instrument = instrumentList.currentItem()
        instrument = instrument.text()
        if instrument == 'SR830':
            openWindowServers(self.SR830_InstrumentSetting,self.Servers,self.Devices)
            self.SR830_InstrumentSetting.refreshServerIndicator()
        if instrument == 'DAC-ADC':
            openWindowServers(self.DACADC_InstrumentSetting,self.Servers,self.Devices)
            self.DACADC_InstrumentSetting.refreshServerIndicator()
            #self.SR830_InstrumentSetting.complete.connect(lambda: ReadInstrumentSetting(self.bus,self.SR830_InstrumentSetting.InstrumentDict['Name'], self.SR830_InstrumentSetting.InstrumentDict))
        if instrument == 'Lakeshore':
            openWindowServers(self.Lakeshore_InstrumentSetting,self.Servers,self.Devices)
            self.Lakeshore_InstrumentSetting.refreshServerIndicator()
        if instrument == 'AMI430':
            openWindowServers(self.Magnet_InstrumentSetting,self.Servers,self.Devices)
            self.Magnet_InstrumentSetting.refreshServerIndicator()
        
        if instrument == 'Keithley2450':
            openWindowServers(self.Keithley2450_InstrumentSetting,self.Servers,self.Devices)
            self.Keithley2450_InstrumentSetting.refreshServerIndicator()
        if instrument == 'CustomVar':
            openWindowServers(self.CustomVar_InstrumentSetting,self.Servers,self.Devices)

        self.RefreshBus()

    def DeleteInstrument(self, BusList):
        instrument_name = BusList.currentItem()
        instrument_name = instrument_name.text()
        del self.bus[instrument_name]
        self.RefreshBus()

    def EditInstrument(self,BusList):
        instrument_name = BusList.currentItem()
        instrument_name = instrument_name.text()
        instrument_type = self.bus[instrument_name]['InstrumentType']
        if instrument_type == 'SR830':
            openEditInstrumentWindow(self.SR830_InstrumentSetting,self.Servers,self.Devices,self.bus[instrument_name])
        elif instrument_type == 'DAC-ADC':
            openEditInstrumentWindow(self.DACADC_InstrumentSetting,self.Servers,self.Devices,self.bus[instrument_name])
        elif instrument_type == 'Lakeshore':
            openEditInstrumentWindow(self.Lakeshore_InstrumentSetting,self.Servers,self.Devices,self.bus[instrument_name])
        elif instrument_type == 'AMI430':
            openEditInstrumentWindow(self.Magnet_InstrumentSetting,self.Servers,self.Devices,self.bus[instrument_name])
        elif instrument_type == 'Keithley2450':
            openEditInstrumentWindow(self.Keithley2450_InstrumentSetting,self.Servers,self.Devices,self.bus[instrument_name])
        elif instrument_type == 'CVar':
            openEditInstrumentWindow(self.CustomVar_InstrumentSetting,self.Servers,self.Devices,self.bus[instrument_name])

    def printInfo(self,devicename, buslist):
        if devicename is not None:
            devicename = devicename.text()
            dictionary = buslist[devicename]
            totalstring = ""
            for key in dictionary:
                if dictionary[key] is not None:
                    totalstring += str(key) + ": " + str(dictionary[key]) + "\n"
            self.textEdit_BusInfo.setText(totalstring)
        else:
            self.textEdit_BusInfo.setText('')

    def RefreshBus(self):
        self.BusList.clear()
        self.BusList.addItems(self.bus.keys())

    def closeBus(self):
        self.busset.emit()
        self.close()

    def clearInfo(self):
        pass
    def moveDefault(self):
        self.move(200,100)
