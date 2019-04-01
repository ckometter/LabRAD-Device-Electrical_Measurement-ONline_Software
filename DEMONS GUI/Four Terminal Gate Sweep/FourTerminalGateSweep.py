from __future__ import division
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import threading
import copy
from scipy.signal import detrend
#importing a bunch of stuff


path = sys.path[0] + r"\Four Terminal Gate Sweep"
print path
FourTerminalGateSweepWindowUI, QtBaseClass = uic.loadUiType(path + r"\FourTerminalGateSweepWindow.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way.
sys.path.append(sys.path[0]+'\Resources')
from DEMONSFormat import *
from DEMONSMeasure import *

class Window(QtGui.QMainWindow, FourTerminalGateSweepWindowUI):

    def __init__(self, reactor, DEMONS, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.parent = parent
        self.DEMONS = DEMONS
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.serversList = { #Dictionary including toplevel server received from labrad connect
            'dv': False,
            'DACADC': False,
            'SR830': False,
            'SR860': False,
        }

        self.DeviceList = {}#self.DeviceList['Device Name'][Device Property]

        self.DeviceList['Voltage_LI_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Voltage_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_Voltage_LI_SelectDevice,
            'ServerIndicator': self.pushButton_Voltage_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_Voltage_LI_DeviceIndicator,            
            'ServerNeeded': ['SR830', 'SR860'],
        }

        self.DeviceList['Current_LI_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Current_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_Current_LI_SelectDevice,
            'ServerIndicator': self.pushButton_Current_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_Current_LI_DeviceIndicator, 
            'ServerNeeded': ['SR860', 'SR830'],
        }

        self.DeviceList['DataAquisition_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_DataAquisition_SelectServer,
            'ComboBoxDevice': self.comboBox_DataAquisition_SelectDevice,
            'ServerIndicator': self.pushButton_DataAquisition_ServerIndicator,
            'DeviceIndicator': self.pushButton_DataAquisition_DeviceIndicator, 
            'ServerNeeded': ['DACADC'],
        }

        self.Parameter = {
            'DeviceName': 'Device Name',#This is related to the sample name like YS8
            'Voltage_LI_Sensitivity': 1,
            'Voltage_LI_Timeconstant': 2,
            'Voltage_LI_Frequency': 17.777,
            'Voltage_LI_Gain': 1.0,
            'Current_LI_Sensitivity': 1,
            'Current_LI_Timeconstant': 2,
            'Current_LI_Frequency': 17.777,
            'Current_LI_Gain': 1.0,
            'FourTerminal_StartVoltage': 0.0,
            'FourTerminal_EndVoltage': 1.0,
            'FourTerminal_Delay': 0.01,
            'FourTerminalSetting_Numberofsteps_Status': "Numberofsteps",
            'FourTerminal_Numberofstep': 1000,
            'FourTerminal_GateChannel': 0,
            'FourTerminal_VoltageReadingChannel': 0,
            'FourTerminal_CurrentReadingChannel': 1,
        } 

        self.lineEdit = {
            'DeviceName': self.lineEdit_Device_Name,
            'Voltage_LI_Sensitivity': self.lineEdit_Voltage_LI_Sensitivity,
            'Voltage_LI_Timeconstant': self.lineEdit_Voltage_LI_Timeconstant,
            'Voltage_LI_Frequency': self.lineEdit_Voltage_LI_Frequency,
            'Voltage_LI_Gain': self.lineEdit_Voltage_LI_Gain,
            'Current_LI_Sensitivity': self.lineEdit_Current_LI_Sensitivity,
            'Current_LI_Timeconstant': self.lineEdit_Current_LI_Timeconstant,
            'Current_LI_Frequency': self.lineEdit_Current_LI_Frequency,
            'Current_LI_Gain': self.lineEdit_Current_LI_Gain,
            'FourTerminal_StartVoltage': self.lineEdit_FourTerminal_StartVoltage,
            'FourTerminal_EndVoltage': self.lineEdit_FourTerminal_EndVoltage,
            'FourTerminal_Delay': self.lineEdit_FourTerminal_Delay,
            'FourTerminal_Numberofstep': self.lineEdit_FourTerminal_Numberofstep,
            'FourTerminal_GateChannel': self.lineEdit_DataAquisition_GateChannel,
            'FourTerminal_VoltageReadingChannel': self.lineEdit_DataAquisition_VoltageChannel,
            'FourTerminal_CurrentReadingChannel': self.lineEdit_DataAquisition_CurrentChannel,
            
        }

        for key in self.lineEdit:
            if not isinstance(self.Parameter[key], str):
                UpdateLineEdit_Bound(self.Parameter, key, self.lineEdit)

        self.DetermineEnableConditions()

        self.FourTerminal_ChannelInput=[]
        self.FourTerminal_ChannelOutput=[]

        self.lineEdit_Device_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.Parameter, 'DeviceName', self.lineEdit))

        self.comboBox_Voltage_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Voltage_LI_Device', self.serversList, str(self.DeviceList['Voltage_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Voltage_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Voltage_LI_Device', str(self.DeviceList['Voltage_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_Voltage_LI_Sensitivity.editingFinished.connect(lambda: UpdateSetlineEdit(self.Parameter, 'Voltage_LI_Sensitivity', self.lineEdit, self.DeviceList['Voltage_LI_Device']['DeviceObject'], ['SR830', 'sensitivity'], [0, 26], int))
        self.lineEdit_Voltage_LI_Timeconstant.editingFinished.connect(lambda: UpdateSetlineEdit(self.Parameter, 'Voltage_LI_Timeconstant', self.lineEdit, self.DeviceList['Voltage_LI_Device']['DeviceObject'], ['SR830', 'timeconstant'], [0, 19], int))
        self.lineEdit_Voltage_LI_Frequency.editingFinished.connect(lambda: UpdateSetlineEdit(self.Parameter, 'Voltage_LI_Frequency', self.lineEdit, self.DeviceList['Voltage_LI_Device']['DeviceObject'], ['SR830', 'frequency'], None, float))
        self.lineEdit_Voltage_LI_Gain.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Voltage_LI_Gain', self.lineEdit))

        self.comboBox_Current_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Current_LI_Device', self.serversList, str(self.DeviceList['Current_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Current_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Current_LI_Device', str(self.DeviceList['Current_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_Current_LI_Sensitivity.editingFinished.connect(lambda: UpdateSetlineEdit(self.Parameter, 'Current_LI_Sensitivity', self.lineEdit, self.DeviceList['Current_LI_Device']['DeviceObject'], ['SR830', 'sensitivity'], [0, 26], int))
        self.lineEdit_Current_LI_Timeconstant.editingFinished.connect(lambda: UpdateSetlineEdit(self.Parameter, 'Current_LI_Timeconstant', self.lineEdit, self.DeviceList['Current_LI_Device']['DeviceObject'], ['SR830', 'timeconstant'], [0, 19], int))
        self.lineEdit_Current_LI_Frequency.editingFinished.connect(lambda: UpdateSetlineEdit(self.Parameter, 'Current_LI_Frequency', self.lineEdit, self.DeviceList['Current_LI_Device']['DeviceObject'], ['SR830', 'frequency'], None, float))
        self.lineEdit_Current_LI_Gain.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Current_LI_Gain', self.lineEdit))

        self.comboBox_DataAquisition_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'DataAquisition_Device', self.serversList, str(self.DeviceList['DataAquisition_Device']['ComboBoxServer'].currentText())))
        self.comboBox_DataAquisition_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'DataAquisition_Device', str(self.DeviceList['DataAquisition_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_FourTerminal_StartVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_StartVoltage', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_FourTerminal_StartVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_EndVoltage', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_FourTerminal_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_Numberofstep.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_Delay.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_Delay', self.lineEdit))
        self.pushButton_FourTerminal_NoSmTpTSwitch.clicked.connect(lambda: Toggle_NumberOfSteps_StepSize(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.label_FourTerminalNumberofstep, 'Volt per Step', self.lineEdit))  

        self.pushButton_StartFourTerminalSweep.clicked.connect(self.StartMeasurement)

        self.SetupPlots()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.lineEdit_Device_Name: True,
            self.pushButton_StartFourTerminalSweep: (not self.DeviceList['DataAquisition_Device'] == False) and self.DEMONS.Scanning_Flag == False,
            self.comboBox_Voltage_LI_SelectDevice: True,
            self.lineEdit_Voltage_LI_Sensitivity: True,
            self.lineEdit_Voltage_LI_Timeconstant: True,
            self.lineEdit_Voltage_LI_Frequency: True,
            self.lineEdit_Voltage_LI_Gain: True,
            self.comboBox_Current_LI_SelectDevice: True,
            self.lineEdit_Current_LI_Sensitivity: True,
            self.lineEdit_Current_LI_Timeconstant: True,
            self.lineEdit_Current_LI_Frequency: True,
            self.lineEdit_Current_LI_Gain: True,
            self.comboBox_DataAquisition_SelectDevice: True,
            self.lineEdit_DataAquisition_GateChannel: any(device in self.comboBox_DataAquisition_SelectDevice.currentText() for device in DACADC_Registry()),
            self.lineEdit_DataAquisition_VoltageChannel: any(device in self.comboBox_DataAquisition_SelectDevice.currentText() for device in DACADC_Registry()),
            self.lineEdit_DataAquisition_CurrentChannel: any(device in self.comboBox_DataAquisition_SelectDevice.currentText() for device in DACADC_Registry()),
        }

    @inlineCallbacks
    def StartMeasurement(self, c):
        if any(device in self.comboBox_DataAquisition_SelectDevice.currentText() for device in DACADC_Registry()): #Determine if seclected device include DACADC in registry
            try:
                ImageNumber, ImageDir = yield CreateDataVaultFile(self.serversList['dv'], 'FourTerminalGateSweep ' + str(self.Parameter['DeviceName']), ('Gate Index', 'Gate Voltage'), ('Voltage', 'Current', 'Resistance', 'Conductance'))
                self.lineEdit_ImageNumber.setText(ImageNumber)
                self.lineEdit_ImageDir.setText(ImageDir)
                yield AddParameterToDataVault(self.serversList['dv'], self.Parameter)

                GateChannel, VoltageChannel, CurrentChannel = self.Parameter['FourTerminal_GateChannel'], self.Parameter['FourTerminal_VoltageReadingChannel'], self.Parameter['FourTerminal_CurrentReadingChannel']
                StartVoltage, EndVoltage = self.Parameter['FourTerminal_StartVoltage'], self.Parameter['FourTerminal_EndVoltage']
                NumberOfSteps, Delay = self.Parameter['FourTerminal_Numberofstep'], self.Parameter['FourTerminal_Delay']
                ClearPlots(self.Plotlist)
                yield Ramp_DACADC(self.DeviceList['DataAquisition_Device'], GateChannel, 0.0, StartVoltage, NumberOfSteps, Delay)
                yield SleepAsync(self.reactor, 1)
                Data = yield Buffer_Ramp_DACADC(self.DeviceList['DataAquisition_Device'], [GateChannel], [VoltageChannel, CurrentChannel],[StartVoltage], [EndVoltage], NumberOfSteps, Delay)
                yield Ramp_DACADC(self.DeviceList['DataAquisition_Device'], GateChannel, EndVoltage, 0.0, NumberOfSteps, Delay)
                Data = Multiply(Data, [1.0, 1.0]) #Scale them with corresponding multiplier [voltage, current]
                Data = AttachData_Front(Data, np.linspace(StartVoltage, EndVoltage, NumberOfSteps)) #Attach Gate Voltage
                Data = AttachData_Front(Data, range(NumberOfSteps)) #Attach Gate Index
                Data = Attach_ResistanceConductance(Data, 2, 3)

                self.serversList['dv'].add(Data)

                XData, VoltageData, CurrentData, ResistanceData, ConductanceData = Data[:,1], Data[:,2], Data[:,3], Data[:,4], Data[:,5]
                Plot1DData(XData, VoltageData, self.Plotlist['VoltagePlot'])
                Plot1DData(XData, CurrentData, self.Plotlist['CurrentPlot'])
                Plot1DData(XData, ResistanceData, self.Plotlist['ResistancePlot'])
                Plot1DData(XData, ConductanceData, self.Plotlist['ConductancePlot'])
            except Exception as inst:
                print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    def connectServer(self, key, server):
        try:
            self.serversList[str(key)] = server
            self.refreshServerIndicator()
        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    '''
    When a server is disconnected, look up which device use the server and disconnect it
    '''
    def disconnectServer(self, ServerName):
        try:
            self.serversList[str(ServerName)] = False

            for key, DevicePropertyList in self.DeviceList.iteritems():
                if str(ServerName) == str(DevicePropertyList['ComboBoxServer'].currentText()):
                    DevicePropertyList['ServerObject'] = False
                    DevicePropertyList['DeviceObject'] = False
            self.refreshServerIndicator()
            self.Refreshinterface()
        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    def refreshServerIndicator(self):
        try:
            optional = []#This optional will reconstruct combobox multiple time when you disconnect/connect server individually
            flag = True
            for key in self.serversList:
                if self.serversList[str(key)] == False and not key in optional:
                    flag = False

            if flag:
                setIndicator(self.pushButton_Servers, 'rgb(0, 170, 0)')

                for key, DevicePropertyList in self.DeviceList.iteritems():#Reconstruct all combobox when all servers are connected
                    ReconstructComboBox(DevicePropertyList['ComboBoxServer'], DevicePropertyList['ServerNeeded'])

                self.Refreshinterface()
            else:
                setIndicator(self.pushButton_Servers, 'rgb(161, 0, 0)')
        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    def Refreshinterface(self):
        print self.serversList
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)

        for key, DevicePropertyList in self.DeviceList.iteritems():
            RefreshIndicator(DevicePropertyList['ServerIndicator'], DevicePropertyList['ServerObject'])
            RefreshIndicator(DevicePropertyList['DeviceIndicator'], DevicePropertyList['DeviceObject'])

    def SetupPlots(self):
        self.Plotlist = {
            'VoltagePlot': pg.PlotWidget(parent = None),
            'CurrentPlot': pg.PlotWidget(parent = None),
            'ResistancePlot': pg.PlotWidget(parent = None),
            'ConductancePlot': pg.PlotWidget(parent = None)
        }
        Setup1DPlot(self.Plotlist['VoltagePlot'], self.Layout_FourTerminalPlot1, 'Voltage', 'Voltage', "V", 'Gate Voltage', "V")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        Setup1DPlot(self.Plotlist['CurrentPlot'], self.Layout_FourTerminalPlot2, 'Current', 'Current', "A", 'Gate Voltage', "V")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        Setup1DPlot(self.Plotlist['ResistancePlot'], self.Layout_FourTerminalPlot3, 'Resistance', 'Resistance', u"\u03A9", 'Gate Voltage', "V")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        Setup1DPlot(self.Plotlist['ConductancePlot'], self.Layout_FourTerminalPlot4, 'Conductance', 'Conductance', "S", 'Gate Voltage',"V" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

    def setSessionFolder(self, folder):
        self.sessionFolder = folder

    def moveDefault(self):
        self.move(200,0)
        
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))