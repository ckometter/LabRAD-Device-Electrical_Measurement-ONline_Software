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
Ui_Setting, QtBaseClass = uic.loadUiType(os.path.join(path , "FourTerminalGateSweepProbeStationSettingWindow.ui"))

class Setting(QtGui.QMainWindow, Ui_Setting):
    def __init__(self, reactor, parent = None):
        super(Setting, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        
        self.parent = parent

        self.lineEdit_Setting_RampDelay.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.parent.Parameter, 'Setting_RampDelay', self.parent.lineEdit))
        self.lineEdit_Setting_RampStepSize.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.parent.Parameter, 'Setting_RampStepSize', self.parent.lineEdit))
        self.lineEdit_Setting_WaitTime.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.parent.Parameter, 'Setting_WaitTime', self.parent.lineEdit))

    def moveDefault(self):
        self.move(200,0)
