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
Ui_CustomVarSetting, QtBaseClass = uic.loadUiType(os.path.join(path , "CustomVarInstrumentSetting.ui"))

class CustomVarSetting(QtGui.QMainWindow, Ui_CustomVarSetting):
    complete = QtCore.pyqtSignal()

    def __init__(self, reactor, parent = None):
        super(CustomVarSetting, self).__init__(parent)
        from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg, s,A 

        self.reactor = reactor
        self.setupUi(self)
        
        self.Servers = {}
        self.Devices = {}

        self.parent = parent

        self.DeviceList = {}



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
            'Name': 'Default',
            'InstrumentType': 'CVar',
            'DefString': None,
            'CustomFn': ReadCustomInstrumentSetting,
        }
        self.lineEdit = {
            'Name': self.lineEdit_Name,
            'DefString': self.lineEdit_Defstring,
        }
        ##Input 
        self.DetermineEnableConditions()

        self.lineEdit_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.InstrumentDict,'Name',self.lineEdit))
        self.lineEdit_Defstring.editingFinished.connect(lambda: UpdateLineEdit_String(self.InstrumentDict,'DefString',self.lineEdit))
        self.pushButton_Done.clicked.connect(lambda: self.done())
        self.pushButton_Cancel.clicked.connect(lambda: self.closeWindow())


    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)
        for key, dlist in self.DeviceList.items():
            RefreshIndicator(dlist['ServerIndicator'],dlist['ServerObject'])
            RefreshIndicator(dlist['DeviceIndicator'],dlist['DeviceObject'])

    def DetermineEnableConditions(self):
        self.ButtonsCondition = {
        }

    def done(self):
        self.complete.emit()
        self.close()

    def closeWindow(self):
        self.close()

    def initialize(self,input_dictionary):
        self.lineEdit_Name.setText(input_dictionary['Name'])
        self.lineEdit_Defstring.setText(input_dictionary['DefString'])

    def clearInfo(self):
        self.InstrumentDict = {
            'Name': 'Default',
            'InstrumentType': 'CVar',
            'DefString': None,
            'CustomFn': ReadCustomInstrumentSetting,
        }

        self.lineEdit_Name.setText('')
        self.lineEdit_Defstring.setText('')

    def moveDefault(self):
        self.move(400,100)

def ReadCustomInstrumentSetting(instrumentDict,variable_list,value_list):
    custom_variable = instrumentDict['DefString']
    operator_list = ['^','*','/','+','-','(',')']
    return loopCustom(variable_list,operator_list, value_list,custom_variable)