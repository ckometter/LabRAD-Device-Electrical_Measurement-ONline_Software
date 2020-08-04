#Written by Raymond
import sys
import os
from PyQt5 import Qt, QtGui, QtWidgets, QtCore, uic
import time 
import ctypes
import traceback
import subprocess

#import exceptions
#myappid = 'YoungLab.DeviceElectricalMeasurementONlineSoftware'
#ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(path, 'Resources'))
sys.path.append(os.path.join(path, 'Labrad Connect'))
sys.path.append(os.path.join(path, 'DataVaultBrowser'))
sys.path.append(os.path.join(path, 'Transport Gate Sweep'))
sys.path.append(os.path.join(path, 'Four Terminal Gate Sweep SQUID'))
sys.path.append(os.path.join(path, 'DAC Controler'))
sys.path.append(os.path.join(path, 'Fridge Status'))
sys.path.append(os.path.join(path, 'DV Plotter'))


UI_path = os.path.join(path, "MainWindow.ui")
MainWindowUI, QtBaseClass = uic.loadUiType(UI_path)

#import all windows for gui
import LabRADConnect
import TransportGateSweep
import FourTerminalGateSweepSQUID
import DACControler
import FridgeStatus
import DVPlotter
import MultiSweeper
from DEMONSFormat import *


class MainWindow(QtGui.QMainWindow, MainWindowUI):
    """ The following section initializes, or defines the initialization of the GUI and 
    connecting to servers."""
    def __init__(self, reactor, parent=None):
        """ DEMONS GUI """
        
        super(MainWindow, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        self.Scanning_Flag = False
        
        #Move to default position
        self.moveDefault()
        
        #Intialize all widgets. 
        self.MeasurementWindows = {
            'LabRAD': LabRADConnect.Window(self.reactor, None),
            'TransportGateSweep': MultiSweeper.Window(self.reactor, self, None),
            #'TwoTerminalGateSweepProbeStationWindow': TwoTerminalGateSweepProbeStation.Window(self.reactor, self, None),
            'DACTrackerWindow': DACControler.Window(self.reactor, None),
            #'FourTerminalGateSweepSQUIDWindow': FourTerminalGateSweepSQUID.Window(self.reactor, self, None),
            'FridgeStatus': FridgeStatus.Window(self.reactor, None),
            'DVPlotterWindow': DVPlotter.Window(self.reactor, None),
        }
        
        self.pushButton_LabRADConnect.clicked.connect(lambda: openWindow(self.MeasurementWindows['LabRAD']))
        self.pushButton_TransportGateSweep.clicked.connect(lambda: openWindow(self.MeasurementWindows['TransportGateSweep']))
        self.pushButton_DACADC_Tracker.clicked.connect(lambda: openWindow(self.MeasurementWindows['DACTrackerWindow']))
        #self.pushButton_FourTerminalGateSweepSQUID.clicked.connect(lambda: openWindow(self.MeasurementWindows['FourTerminalGateSweepSQUIDWindow']))
        #self.pushButton_TwoTerminalGateSweepProbeStation.clicked.connect(lambda: openWindow(self.MeasurementWindows['TwoTerminalGateSweepProbeStationWindow']))
        self.pushButton_FridgeStatus.clicked.connect(lambda: openWindow(self.MeasurementWindows['FridgeStatus']))
        # for homemade data plotter
        #self.pushButton_DataPlotter.clicked.connect(lambda: openWindow(self.MeasurementWindows['DVPlotterWindow']))
        # for afylab data plotter
        self.pushButton_DataPlotter.clicked.connect(lambda: runDVPlotter())
        self.MeasurementWindows['LabRAD'].cxnsignal.connect(self.connect)
        self.MeasurementWindows['LabRAD'].discxnsignal.connect(self.disconnect)
        self.MeasurementWindows['LabRAD'].newSessionFolder.connect(self.distributeSessionFolder)
        
        #Open by default the LabRAD Connect Module and Device Select
        openWindow(self.MeasurementWindows['LabRAD'])
        
    def setupAdditionalUi(self):
        """Some UI elements would not set properly from Qt Designer. These initializations are done here."""
        pass
        
#----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to default opening windows."""
    def connect(self, key, object):
        try:
            for name, window in self.MeasurementWindows.items():
                if name != 'LabRAD': #Skip through labradconnect window
                    if str(key) in window.serversList:
                        window.connectServer(str(key), object)
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2])
            traceback.print_tb(sys.exc_info()[2])

    def disconnect(self, key):
        try:
            for name, window in self.MeasurementWindows.items():
                if name != 'LabRAD': #No module need cxn
                    if str(key) in window.serversList:
                        window.disconnectServer(key)
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
        
    def updateDataVaultFolder(self, DVfolder):
        try:
            for name, window in self.MeasurementWindows.items():
                if 'dv' in window.serversList:
                    window.updateDataVaultDirectory(window, DVfolder)
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def distributeSessionFolder(self, folder):
        try:
            for name, window in self.MeasurementWindows.items():
                setSessionFolder = getattr(window, 'setSessionFolder', None)
                if callable(setSessionFolder):
                    window.setSessionFolder(folder)
        
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def SetScanningFlag(self, State):
        self.Scanning_Flag = State
    
    def moveDefault(self):
        self.move(10,10)
        
    def closeEvent(self, e):
        try:
            self.MeasurementWindows['LabRAD'].close()
        except Exception as inst:
            print(inst)
            
#----------------------------------------------------------------------------------------------#     
""" The following runs the GUI"""

if __name__=="__main__":
    import qt5reactor
    app = QtGui.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    #from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg

    window = MainWindow(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
