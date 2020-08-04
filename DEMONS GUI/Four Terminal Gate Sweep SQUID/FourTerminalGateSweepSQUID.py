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
sys.path.append(os.path.join(path, 'FourTerminalGateSweepSQUIDSetting'))
sys.path.append(os.path.join(path, 'MagneticFieldExpansionPack'))
sys.path.append(os.path.join(path, 'HysterisisExpansionPack'))
sys.path.append(os.path.join(path, 'GateHysteresisExpansionpack'))

import FourTerminalGateSweepSQUIDSetting
import MagnetExtension
import HysteresisExtension
import GateHysteresisExtension

FourTerminalGateSweepSQUIDWindowUI, QtBaseClass = uic.loadUiType(os.path.join(path, "FourTerminalGateSweepSQUIDWindow.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

# Not required, but strongly recommended functions used to format numbers in a particular way.
# sys.path.append(sys.path[0]+'\Resources')

from DEMONSFormat import *
class Window(QtGui.QMainWindow, FourTerminalGateSweepSQUIDWindowUI):
    def __init__(self, reactor, DEMONS, UpperLevel, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.UpperLevel = UpperLevel
        self.DEMONS = DEMONS
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.SettingWindow = FourTerminalGateSweepSQUIDSetting.Setting(self.reactor, self)
        self.pushButton_Setting.clicked.connect(lambda: openWindow(self.SettingWindow))
        self.MagnetControlWindow = MagnetExtension.MagnetControl(self.reactor, self)
        self.pushButton_MagneticField.clicked.connect(lambda: openWindow(self.MagnetControlWindow))
        self.HysteresisWindow = HysteresisExtension.Hysteresis(self.reactor, self)
        self.pushButton_Hysterisis.clicked.connect(lambda: openWindow(self.HysteresisWindow))
        self.GateHysteresisWindow = GateHysteresisExtension.GateHysteresis(self.reactor, self)
        self.pushButton_GateHysterisis.clicked.connect(lambda: openWindow(self.GateHysteresisWindow))
        
        self.serversList = { #Dictionary including toplevel server received from labrad connect
            'dv': False,
            'DACADC': False,
            'SR830': False,
            'SR860': False,
            'AMI430': False,
            '4KMonitor IPS120': False,
            'IPS120': False,
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

        self.DeviceList['Magnet_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.MagnetControlWindow.comboBox_MagnetControl_SelectServer,
            'ComboBoxDevice': self.MagnetControlWindow.comboBox_MagnetControl_SelectDevice,
            'ServerIndicator': self.MagnetControlWindow.pushButton_MagnetControl_ServerIndicator,
            'DeviceIndicator': self.MagnetControlWindow.pushButton_MagnetControl_DeviceIndicator, 
            'ServerNeeded': ['AMI430', '4KMonitor IPS120', 'IPS120'],
        }
        
        self.DeviceList['Hysteresis_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.HysteresisWindow.comboBox_Hysteresis_SelectServer,
            'ComboBoxDevice': self.HysteresisWindow.comboBox_Hysteresis_SelectDevice,
            'ServerIndicator': self.HysteresisWindow.pushButton_Hysteresis_ServerIndicator,
            'DeviceIndicator': self.HysteresisWindow.pushButton_Hysteresis_DeviceIndicator, 
            'ServerNeeded': ['AMI430', '4KMonitor IPS120', 'IPS120'],
        }

        self.Parameter = {
            'DeviceName': 'Device Name',#This is related to the sample name like YS8
            'Voltage_LI_Sensitivity': 0.3,
            'Voltage_LI_Timeconstant': 0.3,
            'Voltage_LI_Excitation': 0.0,
            'Voltage_LI_Frequency': 17.777,
            'Voltage_LI_Gain': 1.0,
            'Current_LI_Sensitivity': 0.003,
            'Current_LI_Timeconstant': 0.3,
            'Current_LI_Frequency': 17.777,
            'Current_LI_Gain': 1.0,
            'FourTerminal_StartVoltage': -0.1,
            'FourTerminal_EndVoltage': 0.1,
            'FourTerminal_Numberofstep': 100,
            'FourTerminal_Delay': 0.001,
            'FourTerminalSetting_Numberofsteps_Status': "Numberofsteps",
            'FourTerminal_GateChannel': 0,
            'FourTerminal_VoltageReadingChannel': 0,
            'FourTerminal_CurrentReadingChannel': 1,
            'Setting_RampDelay': 0.0001,
            'Setting_RampStepSize': 0.001,
            'Setting_WaitTime': 2.0,
            'MagnetControl_StartField': -0.3,
            'MagnetControl_EndField': 0.3,
            'MagnetControl_Numberofstep': 10,
            'MagnetControl_Numberofstep_Status': "Numberofsteps",
            'MagnetControl_RampSpeed': 1.0,
            'MagnetControl_Delay': 0.5,
            'Hysteresis_StartField': -0.3,
            'Hysteresis_EndField': 0.3,
            'Hysteresis_Numberofstep': 10,
            'Hysteresis_Numberofstep_Status': "Numberofsteps",
            'Hysteresis_RampSpeed': 1.0,
            'Hysteresis_Delay': 0.5,
            'GateHysteresis_StartVoltage': -1.0,
            'GateHysteresis_EndVoltage': 1.0,
            'GateHysteresis_Numberofstep': 10,
            'GateHysteresis_Numberofstep_Status': "Numberofsteps",
            'GateHysteresis_Delay': 0.5,
            }

        self.lineEdit = {
            'DeviceName': self.lineEdit_Device_Name,
            'Voltage_LI_Sensitivity': self.lineEdit_Voltage_LI_Sensitivity,
            'Voltage_LI_Timeconstant': self.lineEdit_Voltage_LI_Timeconstant,
            'Voltage_LI_Excitation': self.lineEdit_Voltage_LI_Excitation,
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
            'FourTerminal_GateChannel': self.lineEdit_GateVoltageChannel,
            'FourTerminal_VoltageReadingChannel': self.lineEdit_VoltageReadingChannel,
            'FourTerminal_CurrentReadingChannel': self.lineEdit_CurrentReadingChannel,
            'Setting_RampDelay': self.SettingWindow.lineEdit_Setting_RampDelay,
            'Setting_RampStepSize': self.SettingWindow.lineEdit_Setting_RampStepSize,
            'Setting_WaitTime': self.SettingWindow.lineEdit_Setting_WaitTime,
            'MagnetControl_StartField': self.MagnetControlWindow.lineEdit_StartField,
            'MagnetControl_EndField': self.MagnetControlWindow.lineEdit_EndVoltage,
            'MagnetControl_Numberofstep': self.MagnetControlWindow.lineEdit_Numberofstep,
            'MagnetControl_RampSpeed': self.MagnetControlWindow.lineEdit_RampSpeed,
            'MagnetControl_Delay': self.MagnetControlWindow.lineEdit_Delay,
            'Hysteresis_StartField': self.HysteresisWindow.lineEdit_StartField,
            'Hysteresis_EndField': self.HysteresisWindow.lineEdit_EndVoltage,
            'Hysteresis_Numberofstep': self.HysteresisWindow.lineEdit_Numberofstep,
            'Hysteresis_RampSpeed': self.HysteresisWindow.lineEdit_RampSpeed,
            'Hysteresis_Delay': self.HysteresisWindow.lineEdit_Delay,
            'GateHysteresis_StartVoltage': self.GateHysteresisWindow.lineEdit_StartVoltage,
            'GateHysteresis_EndVoltage': self.GateHysteresisWindow.lineEdit_EndVoltage,
            'GateHysteresis_Numberofstep': self.GateHysteresisWindow.lineEdit_Numberofstep,
            'GateHysteresis_Delay': self.GateHysteresisWindow.lineEdit_Delay,
            }

        for key in self.lineEdit:
            if not isinstance(self.Parameter[key], str):
                UpdateLineEdit_Bound(self.Parameter, key, self.lineEdit)


        self.Plotlist = {}
        self.Plotlist['VoltagePlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_FourTerminalPlot_1,
            'Title': 'Voltage',
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Voltage',
            'YUnit': "V",
        }
        self.Plotlist['CurrentPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_FourTerminalPlot_2,
            'Title': 'Current',
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Current',
            'YUnit': "A",
        }
        self.Plotlist['ResistancePlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_FourTerminalPlot_3,
            'Title': 'Resistance',
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Resistance',
            'YUnit': u"\u03A9", #Capital Ohm 
        }

        self.lineEdit_Device_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.Parameter, 'DeviceName', self.lineEdit))

        self.comboBox_Voltage_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Voltage_LI_Device', self.serversList, str(self.DeviceList['Voltage_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Voltage_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Voltage_LI_Device', str(self.DeviceList['Voltage_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_Voltage_LI_Sensitivity.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Voltage_LI_Sensitivity', self.lineEdit))
        self.pushButton_Voltage_LI_Sensitivity_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sensitivity, self.Parameter, 'Voltage_LI_Sensitivity', self.lineEdit['Voltage_LI_Sensitivity']))
        self.pushButton_Voltage_LI_Sensitivity_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sensitivity, self.Parameter, 'Voltage_LI_Sensitivity', self.lineEdit['Voltage_LI_Sensitivity']))
        self.lineEdit_Voltage_LI_Timeconstant.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Voltage_LI_Timeconstant', self.lineEdit))
        self.pushButton_Voltage_LI_Timeconstant_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'Voltage_LI_Timeconstant', self.lineEdit['Voltage_LI_Timeconstant']))
        self.pushButton_Voltage_LI_Timeconstant_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'Voltage_LI_Timeconstant', self.lineEdit['Voltage_LI_Timeconstant']))
        self.lineEdit_Voltage_LI_Excitation.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Voltage_LI_Excitation', self.lineEdit))
        self.pushButton_Voltage_LI_Excitation_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'Voltage_LI_Excitation', self.lineEdit['Voltage_LI_Excitation']))
        self.pushButton_Voltage_LI_Excitation_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'Voltage_LI_Excitation', self.lineEdit['Voltage_LI_Excitation']))
        self.lineEdit_Voltage_LI_Frequency.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Voltage_LI_Frequency', self.lineEdit))
        self.pushButton_Voltage_LI_Frequency_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'Voltage_LI_Frequency', self.lineEdit['Voltage_LI_Frequency']))
        self.pushButton_Voltage_LI_Frequency_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'Voltage_LI_Frequency', self.lineEdit['Voltage_LI_Frequency']))
        self.lineEdit_Voltage_LI_Gain.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Voltage_LI_Gain', self.lineEdit))

        self.comboBox_Current_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Current_LI_Device', self.serversList, str(self.DeviceList['Current_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Current_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Current_LI_Device', str(self.DeviceList['Current_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_Current_LI_Sensitivity.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Current_LI_Sensitivity', self.lineEdit))
        self.pushButton_Current_LI_Sensitivity_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sensitivity, self.Parameter, 'Current_LI_Sensitivity', self.lineEdit['Current_LI_Sensitivity']))
        self.pushButton_Current_LI_Sensitivity_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sensitivity, self.Parameter, 'Current_LI_Sensitivity', self.lineEdit['Current_LI_Sensitivity']))
        self.lineEdit_Current_LI_Timeconstant.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Current_LI_Timeconstant', self.lineEdit))
        self.pushButton_Current_LI_Timeconstant_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'Current_LI_Timeconstant', self.lineEdit['Current_LI_Timeconstant']))
        self.pushButton_Current_LI_Timeconstant_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'Current_LI_Timeconstant', self.lineEdit['Current_LI_Timeconstant']))
        self.lineEdit_Current_LI_Frequency.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Current_LI_Frequency', self.lineEdit))
        self.pushButton_Current_LI_Frequency_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'Current_LI_Frequency', self.lineEdit['Current_LI_Frequency']))
        self.pushButton_Current_LI_Frequency_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'Current_LI_Frequency', self.lineEdit['Current_LI_Frequency']))
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

        self.lineEdit_GateVoltageChannel.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_GateChannel', self.lineEdit, None, int))
        self.lineEdit_VoltageReadingChannel.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_VoltageReadingChannel', self.lineEdit, None, int))
        self.lineEdit_CurrentReadingChannel.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_CurrentReadingChannel', self.lineEdit, None, int))

        self.pushButton_StartFourTerminalSweep.clicked.connect(self.StartMeasurement)

        self.SetupPlots()
        self.Refreshinterface()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.lineEdit_Device_Name: True,
            self.pushButton_StartFourTerminalSweep: self.DeviceList['DataAquisition_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False and self.serversList['dv'] != False,
            self.pushButton_AbortFourTerminalSweep: False,
            self.comboBox_Voltage_LI_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Voltage_LI_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Voltage_LI_Sensitivity: self.DEMONS.Scanning_Flag == False,
            self.pushButton_Voltage_LI_Sensitivity_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_Voltage_LI_Sensitivity_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Voltage_LI_Timeconstant: self.DEMONS.Scanning_Flag == False,
            self.pushButton_Voltage_LI_Timeconstant_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_Voltage_LI_Timeconstant_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Voltage_LI_Excitation: self.DEMONS.Scanning_Flag == False,
            self.pushButton_Voltage_LI_Excitation_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_Voltage_LI_Excitation_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Voltage_LI_Frequency: self.DEMONS.Scanning_Flag == False,
            self.pushButton_Voltage_LI_Frequency_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_Voltage_LI_Frequency_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Voltage_LI_Gain: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Current_LI_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Current_LI_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Current_LI_Sensitivity: self.DEMONS.Scanning_Flag == False,
            self.pushButton_Current_LI_Sensitivity_Read: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_Current_LI_Sensitivity_Set: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Current_LI_Timeconstant: self.DEMONS.Scanning_Flag == False,
            self.pushButton_Current_LI_Timeconstant_Read: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_Current_LI_Timeconstant_Set: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Current_LI_Frequency: self.DEMONS.Scanning_Flag == False,
            self.pushButton_Current_LI_Frequency_Read: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_Current_LI_Frequency_Set: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_Current_LI_Gain: self.DEMONS.Scanning_Flag == False,
            self.comboBox_DataAquisition_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_DataAquisition_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_StartVoltage: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_EndVoltage: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_Numberofstep: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_Delay: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_GateVoltageChannel: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_VoltageReadingChannel: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_CurrentReadingChannel: self.DEMONS.Scanning_Flag == False,
        }

    @inlineCallbacks
    def StartMeasurement(self, c):
        try:
            self.DEMONS.SetScanningFlag(True)
            self.Refreshinterface()

            Multiplier = [self.Parameter['Voltage_LI_Sensitivity'] * self.Parameter['Voltage_LI_Gain'] / 10.0, self.Parameter['Current_LI_Sensitivity'] * self.Parameter['Current_LI_Gain'] / 10.0] #Voltage, Current

            ImageNumber, ImageDir = yield CreateDataVaultFile(self.serversList['dv'], 'FourTerminalGateSweep ' + str(self.Parameter['DeviceName']), ('Gate Index', 'Gate Voltage'), ('Voltage', 'Current', 'Resistance', 'Conductance'))
            self.lineEdit_ImageNumber.setText(ImageNumber)
            self.lineEdit_ImageDir.setText(ImageDir)

            yield AddParameterToDataVault(self.serversList['dv'], self.Parameter)
            ClearPlots(self.Plotlist)

            GateChannel, VoltageChannel, CurrentChannel = self.Parameter['FourTerminal_GateChannel'], self.Parameter['FourTerminal_VoltageReadingChannel'], self.Parameter['FourTerminal_CurrentReadingChannel']
            StartVoltage, EndVoltage = self.Parameter['FourTerminal_StartVoltage'], self.Parameter['FourTerminal_EndVoltage']
            NumberOfSteps, Delay = self.Parameter['FourTerminal_Numberofstep'], self.Parameter['FourTerminal_Delay']

            yield Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'], GateChannel, 0.0, StartVoltage, self.Parameter['Setting_RampStepSize'], self.Parameter['Setting_RampDelay'])
            yield SleepAsync(self.reactor, self.Parameter['Setting_WaitTime'])

            Data = yield Buffer_Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'], [GateChannel], [VoltageChannel, CurrentChannel],[StartVoltage], [EndVoltage], NumberOfSteps, Delay)
            
            Data = Multiply(Data, Multiplier) #Scale them with corresponding multiplier [voltage, current]
            Data = AttachData_Front(Data, np.linspace(StartVoltage, EndVoltage, NumberOfSteps)) #Attach Gate Voltage
            Data = AttachData_Front(Data, range(NumberOfSteps)) #Attach Gate Index
            Data = Attach_ResistanceConductance(Data, 2, 3)
            self.serversList['dv'].add(Data)

            self.Plotlist['VoltagePlot']['PlotData'][0], self.Plotlist['CurrentPlot']['PlotData'][0], self.Plotlist['ResistancePlot']['PlotData'][0] = Data[:,1], Data[:,1] ,Data[:,1]
            self.Plotlist['VoltagePlot']['PlotData'][1] = Data[:,2]
            self.Plotlist['CurrentPlot']['PlotData'][1] = Data[:,3]
            self.Plotlist['ResistancePlot']['PlotData'][1] = Data[:,4]

            RefreshPlot1D(self.Plotlist)

            yield self.FinishSweep(EndVoltage)

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    @inlineCallbacks
    def FinishSweep(self, currentvoltage):
        try:
            yield SleepAsync(self.reactor, self.Parameter['Setting_WaitTime'])
            yield Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'], int(self.Parameter['FourTerminal_GateChannel']), currentvoltage, 0.0, self.Parameter['Setting_RampStepSize'], self.Parameter['Setting_RampDelay'])
            self.serversList['dv'].add_comment(str(self.textEdit_Comment.toPlainText()))
            self.DEMONS.SetScanningFlag(False)
            self.Refreshinterface()
            saveDataToSessionFolder(self.winId(), self.sessionFolder, str(self.lineEdit_ImageNumber.text()) + ' - ' + 'Four Terminal SQUID ' + self.Parameter['DeviceName'])

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    def connectServer(self, key, server):
        try:
            self.serversList[str(key)] = server
            for name, DevicePropertyList in self.DeviceList.items():#Reconstruct all combobox when all servers are connected
                if key in DevicePropertyList['ServerNeeded']:
                    ReconstructComboBox(DevicePropertyList['ComboBoxServer'], DevicePropertyList['ServerNeeded'])
            self.refreshServerIndicator()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    '''
    When a server is disconnected, look up which device use the server and disconnect it
    '''
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
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    def refreshServerIndicator(self):
        try:
            optional_Main = ['4KMonitor IPS120', 'AMI430', 'IPS120', 'SR830', 'SR860']
            optional_MagneticExtension = ['SR830', 'SR860']
            optional_HysteresisExtension = ['SR830', 'SR860']
            flag_Main, flag_MagneticExtension, flag_HysteresisExtension = True, True, True
            for key in self.serversList:
                if self.serversList[str(key)] == False and not key in optional_Main:
                    flag_Main = False
                if self.serversList[str(key)] == False and not key in optional_MagneticExtension:
                    flag_MagneticExtension = False
                if self.serversList[str(key)] == False and not key in optional_HysteresisExtension:
                    flag_HysteresisExtension = False
                    
            if flag_Main:
                setIndicator(self.pushButton_Servers, 'rgb(0, 170, 0)')
                setIndicator(self.GateHysteresisWindow.pushButton_Servers, 'rgb(0, 170, 0)')
                if flag_MagneticExtension:
                    setIndicator(self.MagnetControlWindow.pushButton_Servers, 'rgb(0, 170, 0)')
                if flag_HysteresisExtension:
                    setIndicator(self.HysteresisWindow.pushButton_Servers, 'rgb(0, 170, 0)')
                    
                self.Refreshinterface()
            else:
                setIndicator(self.pushButton_Servers, 'rgb(161, 0, 0)')
                setIndicator(self.MagnetControlWindow.pushButton_Servers, 'rgb(161, 0, 0)')
                setIndicator(self.HysteresisWindow.pushButton_Servers, 'rgb(161, 0, 0)')
                setIndicator(self.GateHysteresisWindow.pushButton_Servers, 'rgb(161, 0, 0)')
                
        except Exception as inst:
            print('Error: refreshServerIndicator', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)

        for key, DevicePropertyList in self.DeviceList.items():
            RefreshIndicator(DevicePropertyList['ServerIndicator'], DevicePropertyList['ServerObject'])
            RefreshIndicator(DevicePropertyList['DeviceIndicator'], DevicePropertyList['DeviceObject'])

        self.MagnetControlWindow.Refreshinterface()
        self.HysteresisWindow.Refreshinterface()
        self.GateHysteresisWindow.Refreshinterface()

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
