from __future__ import division
import sys
import os
import twisted
from PyQt5 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
import numpy as np
import pyqtgraph as pg
#import exceptions
import time
import threading
import copy
from scipy.signal import detrend
#importing a bunch of stuff


path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(path, 'FourTerminalGateSweepProbeStationSetting'))

import FourTerminalGateSweepProbeStationSetting

FourTerminalGateSweepProbeStationWindowUI, QtBaseClass = uic.loadUiType(os.path.join(path, "FourTerminalGateSweepProbeStationWindow.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

#Not required, but strongly recommended functions used to format numbers in a particular way.
#sys.path.append(sys.path[0]+'\Resources')
from DEMONSFormat import *

class Window(QtGui.QMainWindow, FourTerminalGateSweepProbeStationWindowUI):

    def __init__(self, reactor, DEMONS, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.parent = parent
        self.DEMONS = DEMONS
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.SettingWindow = FourTerminalGateSweepProbeStationSetting.Setting(self.reactor, self)
        self.pushButton_Setting.clicked.connect(lambda: openWindow(self.SettingWindow))

        self.serversList = { #Dictionary including toplevel server received from labrad connect
            'dv': False,
            'DACADC': False,
            'SR830': False,
            'SR860': False,
            'SIM900': False,
        }

        self.DeviceList = {}#self.DeviceList['Device Name'][Device Property]

        self.DeviceList['Voltage_LI_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Voltage_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_Voltage_LI_SelectDevice,
            'ServerIndicator': self.pushButton_Voltage_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_Voltage_LI_DeviceIndicator,
            'ServerNeeded': ['SR860', 'SR830'],
        }

        self.DeviceList['Current_LI_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Current_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_Current_LI_SelectDevice,
            'ServerIndicator': self.pushButton_Current_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_Current_LI_DeviceIndicator, 
            'ServerNeeded': ['SR830', 'SR860'],
        }

        self.DeviceList['DataAquisition_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_DataAquisition_SelectServer,
            'ComboBoxDevice': self.comboBox_DataAquisition_SelectDevice,
            'ServerIndicator': self.pushButton_DataAquisition_ServerIndicator,
            'DeviceIndicator': self.pushButton_DataAquisition_DeviceIndicator, 
            'ServerNeeded': ['SIM900'],
        }

        self.Parameter = {
            'DeviceName': 'Device Name',#This is related to the sample name like YS8
            'LI_Excitation': 0.0,
            'LI_Timeconstant': 0.1,
            'LI_Frequency': 17.777,
            'Voltage_LI_Gain': 1.0,
            'Current_LI_Gain': 1.0,
            'FourTerminal_StartVoltage': -1.0,
            'FourTerminal_EndVoltage': 1.0,
            'FourTerminal_Delay': 0.3,
            'FourTerminalSetting_Numberofsteps_Status': "Numberofsteps",
            'FourTerminal_Numberofstep': 101,
            'FourTerminal_GateChannel': 3,
            'Setting_RampDelay': 0.0001,
            'Setting_RampStepSize': 0.01,
            'Setting_WaitTime': 2.0,
        } 

        self.lineEdit = {
            'DeviceName': self.lineEdit_Device_Name,
            'LI_Excitation': self.lineEdit_LI_Excitation,
            'LI_Timeconstant': self.lineEdit_LI_Timeconstant,
            'LI_Frequency': self.lineEdit_LI_Frequency,
            'FourTerminal_StartVoltage': self.lineEdit_FourTerminal_StartVoltage,
            'FourTerminal_EndVoltage': self.lineEdit_FourTerminal_EndVoltage,
            'FourTerminal_Delay': self.lineEdit_FourTerminal_Delay,
            'FourTerminal_Numberofstep': self.lineEdit_FourTerminal_Numberofstep,
            'FourTerminal_GateChannel': self.lineEdit_DataAquisition_GateChannel,
            'Setting_RampDelay': self.SettingWindow.lineEdit_Setting_RampDelay,
            'Setting_RampStepSize': self.SettingWindow.lineEdit_Setting_RampStepSize,
            'Setting_WaitTime': self.SettingWindow.lineEdit_Setting_WaitTime,
        }

        for key in self.lineEdit:
            if not isinstance(self.Parameter[key], str):
                UpdateLineEdit_Bound(self.Parameter, key, self.lineEdit)


        self.Plotlist = {}
        self.Plotlist['VoltagePlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_FourTerminalPlot1,
            'Title': 'Voltage',
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Voltage',
            'YUnit': "V",
        }

        self.Plotlist['CurrentPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_FourTerminalPlot2,
            'Title': 'Current',
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Current',
            'YUnit': "A",
        }

        self.Plotlist['ResistancePlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_FourTerminalPlot3,
            'Title': 'Resistance',
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Resistance',
            'YUnit': u"\u03A9", #Capital Ohm 
        }


        self.DetermineEnableConditions()

        self.lineEdit_Device_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.Parameter, 'DeviceName', self.lineEdit))

        self.lineEdit_LI_Excitation.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Excitation', self.lineEdit))
        # self.pushButton_LI_Excitation_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation']))
        # self.pushButton_LI_Excitation_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation']))#Send to Voltage Lock in
        self.lineEdit_LI_Timeconstant.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Timeconstant', self.lineEdit))
        # self.pushButton_LI_Timeconstant_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant']))
        # self.pushButton_LI_Timeconstant_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant']))#Send to Voltage Lock in
        # self.pushButton_LI_Timeconstant_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant']))#Send to Current Lock in
        self.lineEdit_LI_Frequency.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Frequency', self.lineEdit))
        # self.pushButton_LI_Frequency_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency']))
        # self.pushButton_LI_Frequency_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency']))#Send to Voltage Lock in
        # self.pushButton_LI_Frequency_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency']))#Send to Current Lock in

        self.comboBox_Voltage_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Voltage_LI_Device', self.serversList, str(self.DeviceList['Voltage_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Voltage_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Voltage_LI_Device', str(self.DeviceList['Voltage_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        
        self.comboBox_Current_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Current_LI_Device', self.serversList, str(self.DeviceList['Current_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Current_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Current_LI_Device', str(self.DeviceList['Current_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))

        self.comboBox_DataAquisition_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'DataAquisition_Device', self.serversList, str(self.DeviceList['DataAquisition_Device']['ComboBoxServer'].currentText())))
        self.comboBox_DataAquisition_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'DataAquisition_Device', str(self.DeviceList['DataAquisition_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_DataAquisition_GateChannel.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_GateChannel', self.lineEdit, None, int))


        self.lineEdit_FourTerminal_StartVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_StartVoltage', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_FourTerminal_StartVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_EndVoltage', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_FourTerminal_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_Numberofstep.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_Delay.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_Delay', self.lineEdit))
        self.pushButton_FourTerminal_NoSmTpTSwitch.clicked.connect(lambda: Toggle_NumberOfSteps_StepSize(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.label_FourTerminalNumberofstep, 'Volt per Step', self.lineEdit))  

        self.pushButton_StartFourTerminalSweep.clicked.connect(self.StartMeasurement)
        self.pushButton_AbortFourTerminalSweep.clicked.connect(lambda: self.DEMONS.SetScanningFlag(False))

        self.SetupPlots()
        self.Refreshinterface()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.lineEdit_Device_Name: True,
            self.pushButton_StartFourTerminalSweep: (self.DeviceList['DataAquisition_Device']['DeviceObject'] != False) and (self.DeviceList['Current_LI_Device']['DeviceObject'] != False) and (self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False) and self.DEMONS.Scanning_Flag == False,
            self.pushButton_AbortFourTerminalSweep: self.DEMONS.Scanning_Flag == True,
            self.comboBox_DataAquisition_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_DataAquisition_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_DataAquisition_GateChannel: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_StartVoltage: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_EndVoltage: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_Numberofstep: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_Delay: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Timeconstant: self.DEMONS.Scanning_Flag == False,
            # self.pushButton_LI_Timeconstant_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            # self.pushButton_LI_Timeconstant_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Frequency: self.DEMONS.Scanning_Flag == False,
            # self.pushButton_LI_Frequency_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            # self.pushButton_LI_Frequency_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.comboBox_Voltage_LI_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Voltage_LI_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Excitation: self.DEMONS.Scanning_Flag == False,
            # self.pushButton_LI_Excitation_Read: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            # self.pushButton_LI_Excitation_Set: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.comboBox_Current_LI_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Current_LI_SelectDevice: self.DEMONS.Scanning_Flag == False,
        }

    @inlineCallbacks
    def StartMeasurement(self, c):
        try:
            self.DEMONS.SetScanningFlag(True)#Set scanning flag to be True, this is a flag in DEMON main Window and it is used for preventing to start multiple measurements
    
            self.Refreshinterface()#Based on flag, disable buttons
            
            #At the beginning of the measurement, set the parameters to the lock-in
            SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant'])
            SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant'])
            SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'])
            SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'])
            SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation'])
    
            Multiplier = [self.Parameter['Voltage_LI_Gain'], self.Parameter['Current_LI_Gain']] #Voltage, Current for multiply the data
    
            ImageNumber, ImageDir = yield CreateDataVaultFile(self.serversList['dv'], 'FourTerminalGateSweep ' + str(self.Parameter['DeviceName']), ('Gate Index', 'Gate Voltage'), ('Voltage', 'Current', 'Resistance', 'Conductance')) #Create datavault with independent variables and dependent variables, this return the datavault number and the directory
            self.lineEdit_ImageNumber.setText(ImageNumber) #set text on lineedit in GUI
            self.lineEdit_ImageDir.setText(ImageDir) #set text on lineedit in GUI
    
            yield AddParameterToDataVault(self.serversList['dv'], self.Parameter) #Add parameters to data vault
            ClearPlots(self.Plotlist) #Clear plots
    
            GateChannel = self.Parameter['FourTerminal_GateChannel']
            StartVoltage, EndVoltage = self.Parameter['FourTerminal_StartVoltage'], self.Parameter['FourTerminal_EndVoltage']
            NumberOfSteps, Delay = self.Parameter['FourTerminal_Numberofstep'], self.Parameter['FourTerminal_Delay']
    
            yield Ramp_SIM900_VoltageSource(self.DeviceList['DataAquisition_Device']['DeviceObject'], GateChannel, 0.0, StartVoltage, self.Parameter['Setting_RampStepSize'], self.Parameter['Setting_RampDelay'], self.reactor)#Ramp to initial voltage
            yield SleepAsync(self.reactor, self.Parameter['Setting_WaitTime'])#Wait the time for everything to settle down
    
            Data = np.empty((0,6)) #Generate empty data with the correct dimension
            GateVoltageSet = np.linspace(StartVoltage, EndVoltage, NumberOfSteps) #Generate Gate Voltage at which to set
            for GateIndex in range(NumberOfSteps): #Sweep all the Gate Voltage
                if self.DEMONS.Scanning_Flag == False: #Check if Aborted, if so, end the sweep
                    print('Abort the Sweep')
                    yield self.FinishSweep(GateVoltageSet[GateIndex])
                    break #Break it outside of the for loop
                yield Set_SIM900_VoltageOutput(self.DeviceList['DataAquisition_Device']['DeviceObject'], GateChannel, GateVoltageSet[GateIndex]) #Set the voltage to the correct voltage
                yield SleepAsync(self.reactor, Delay) #Wait proper amount of time for lock-in
                Voltage = yield Get_SR_LI_R(self.DeviceList['Voltage_LI_Device']['DeviceObject'])#Read voltage from lock-in
                Current = yield Get_SR_LI_R(self.DeviceList['Current_LI_Device']['DeviceObject'])#Read current from lock-in
                
                Data_Line = np.array([Voltage, Current])#make data into a list
                Data_Line = Multiply(Data_Line, Multiplier)#Multitply data 
                Data_Line = AttachData_Front(Data_Line, GateVoltageSet[GateIndex]) #Attach gate voltage
                Data_Line = AttachData_Front(Data_Line, GateIndex) #Attach gate index
                Data_Line = Attach_ResistanceConductance(Data_Line, 2, 3) #Attach resistance and conductance, after this step, the data is 1 by 6
                
                self.serversList['dv'].add(Data_Line) #Add the data to datavault
                
                Data = np.append(Data, [Data_Line], axis = 0)#Meta data for plotting
                XData, VoltageData, CurrentData, ResistanceData, ConductanceData = Data[:,1], Data[:,2], Data[:,3], Data[:,4], Data[:,5]#Generate data for plotting
                ClearPlots(self.Plotlist)#Plotting
                Plot1DData(XData, VoltageData, self.Plotlist['VoltagePlot']['PlotObject'], 'r')#Plotting
                Plot1DData(XData, CurrentData, self.Plotlist['CurrentPlot']['PlotObject'], 'r')#Plotting
                Plot1DData(XData, ResistanceData, self.Plotlist['ResistancePlot']['PlotObject'], 'r')#Plotting
                if GateIndex == NumberOfSteps - 1:#When reach the end of the voltage, finish the sweep
                    yield self.FinishSweep(GateVoltageSet[GateIndex])

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    @inlineCallbacks
    def FinishSweep(self, currentvoltage):
        try:
            yield SleepAsync(self.reactor, self.Parameter['Setting_WaitTime'])
            yield Ramp_SIM900_VoltageSource(self.DeviceList['DataAquisition_Device']['DeviceObject'], self.Parameter['FourTerminal_GateChannel'], currentvoltage, 0.0, self.Parameter['Setting_RampStepSize'], self.Parameter['Setting_RampDelay'], self.reactor)
            self.serversList['dv'].add_comment(str(self.textEdit_Comment.toPlainText()))
            self.DEMONS.SetScanningFlag(False)
            self.Refreshinterface()
            saveDataToSessionFolder(self.winId(), self.sessionFolder, str(self.lineEdit_ImageDir.text()).replace('\\','_') + '_' + str(self.lineEdit_ImageNumber.text())+ ' - ' + 'Probe Station Screening ' + self.Parameter['DeviceName'])

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    def connectServer(self, key, server):
        try:
            self.serversList[str(key)] = server
            self.refreshServerIndicator()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)

        for key, DevicePropertyList in self.DeviceList.items():
            RefreshIndicator(DevicePropertyList['ServerIndicator'], DevicePropertyList['ServerObject'])
            RefreshIndicator(DevicePropertyList['DeviceIndicator'], DevicePropertyList['DeviceObject'])

        if self.DeviceList['Current_LI_Device']['DeviceObject'] != False:
            SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation'])
            SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter,  'LI_Timeconstant', self.lineEdit['LI_Timeconstant'])
            SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'])

    def SetupPlots(self):
        for PlotName in self.Plotlist:
            Setup1DPlot(self.Plotlist[PlotName]['PlotObject'], self.Plotlist[PlotName]['Layout'], self.Plotlist[PlotName]['Title'], self.Plotlist[PlotName]['YAxisName'], self.Plotlist[PlotName]['YUnit'], self.Plotlist[PlotName]['XAxisName'], self.Plotlist[PlotName]['XUnit'])#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

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
