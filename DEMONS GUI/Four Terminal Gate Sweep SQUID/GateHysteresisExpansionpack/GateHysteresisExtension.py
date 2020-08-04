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

from DEMONSFormat import *

path = os.path.dirname(os.path.realpath(__file__))
Ui_GateHysteresisWindow, QtBaseClass = uic.loadUiType(os.path.join(path, "GateHysteresisExtensionWindow.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

class GateHysteresis(QtGui.QMainWindow, Ui_GateHysteresisWindow):
    def __init__(self, reactor, UpperLevel, parent = None):
        super(GateHysteresis, self).__init__(parent)

        self.reactor = reactor
        self.UpperLevel = UpperLevel
        self.parent = parent
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.lineEdit_StartVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'GateHysteresis_StartVoltage', self.UpperLevel.lineEdit))
        self.lineEdit_StartVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'GateHysteresis_Numberofstep', 'GateHysteresis_EndVoltage', 'GateHysteresis_StartVoltage', 'GateHysteresis_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.lineEdit_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'GateHysteresis_EndVoltage', self.UpperLevel.lineEdit))
        self.lineEdit_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'GateHysteresis_Numberofstep', 'GateHysteresis_EndVoltage', 'GateHysteresis_StartVoltage', 'GateHysteresis_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.lineEdit_Numberofstep.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'GateHysteresis_Numberofstep', 'GateHysteresis_EndVoltage', 'GateHysteresis_StartVoltage', 'GateHysteresis_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.pushButton_GateHysteresis_NoSmTpTSwitch.clicked.connect(lambda: Toggle_NumberOfSteps_StepSize(self.UpperLevel.Parameter, 'GateHysteresis_Numberofstep', 'GateHysteresis_EndVoltage', 'GateHysteresis_StartVoltage', 'GateHysteresis_Numberofstep_Status', self.label_Hysteresis_NumberofStep, 'Tesla per Step', self.UpperLevel.lineEdit))  
        self.lineEdit_Delay.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'GateHysteresis_Delay', self.UpperLevel.lineEdit))

        self.pushButton_StartHysteresisSweep.clicked.connect(self.StartMeasurement)
        self.pushButton_AbortHysteresisSweep.clicked.connect(lambda: self.UpperLevel.DEMONS.SetScanningFlag(False))

        self.Plotlist = {}
        self.Plotlist['ResistanceForthPlot'] = {
            'PlotObject': None,
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Resistance_Forth_2DPlot,
            'Title': 'Resistance',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['ResistanceForthPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Resistance_Forth_YZ,
            'Title': None,
            'XAxisName': 'Resistance',
            'XUnit': u"\u03A9",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Resistance_Forth_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['ResistanceForthPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Resistance_Forth_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Resistance',
            'YUnit': u"\u03A9", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Resistance_Forth_XZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['VoltageForthPlot'] = {
            'PlotObject': None,
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Voltage_Forth_2DPlot,
            'Title': 'Voltage',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['VoltageForthPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Voltage_Forth_YZ,
            'Title': None,
            'XAxisName': 'Voltage',
            'XUnit':"V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Voltage_Forth_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['VoltageForthPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Voltage_Forth_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Voltage',
            'YUnit': "V", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Voltage_Forth_XZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['CurrentForthPlot'] = {
            'PlotObject': None, #Define in Setup2DPlot
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Current_Forth_2DPlot,
            'Title': 'Current',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['CurrentForthPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Current_Forth_YZ,
            'Title': None,
            'XAxisName': 'Current',
            'XUnit':"A",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Current_Forth_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['CurrentForthPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Current_Forth_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Current',
            'YUnit': "A", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Current_Forth_XZLineCut,
            'Value': 0.0,
        }
        
        self.Plotlist['ResistanceBackPlot'] = {
            'PlotObject': None,
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Resistance_Back_2DPlot,
            'Title': 'Resistance',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['ResistanceBackPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Resistance_Back_YZ,
            'Title': None,
            'XAxisName': 'Resistance',
            'XUnit': u"\u03A9",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Resistance_Back_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['ResistanceBackPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Resistance_Back_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Resistance',
            'YUnit': u"\u03A9", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Resistance_Back_XZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['VoltageBackPlot'] = {
            'PlotObject': None,
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Voltage_Back_2DPlot,
            'Title': 'Voltage',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['VoltageBackPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Voltage_Back_YZ,
            'Title': None,
            'XAxisName': 'Voltage',
            'XUnit':"V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Voltage_Back_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['VoltageBackPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Voltage_Back_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Voltage',
            'YUnit': "V", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Voltage_Back_XZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['CurrentBackPlot'] = {
            'PlotObject': None, #Define in Setup2DPlot
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Current_Back_2DPlot,
            'Title': 'Current',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['CurrentBackPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Current_Back_YZ,
            'Title': None,
            'XAxisName': 'Current',
            'XUnit':"A",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Current_Back_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['CurrentBackPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Current_Back_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Current',
            'YUnit': "A", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Current_Back_XZLineCut,
            'Value': 0.0,
        }
        
        self.Plotlist['ResistanceSubtractPlot'] = {
            'PlotObject': None,
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Resistance_Subtract_2DPlot,
            'Title': 'Resistance',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['ResistanceSubtractPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Resistance_Subtract_YZ,
            'Title': None,
            'XAxisName': 'Resistance',
            'XUnit': u"\u03A9",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Resistance_Subtract_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['ResistanceSubtractPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Resistance_Subtract_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Resistance',
            'YUnit': u"\u03A9", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Resistance_Subtract_XZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['VoltageSubtractPlot'] = {
            'PlotObject': None,
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Voltage_Subtract_2DPlot,
            'Title': 'Voltage',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['VoltageSubtractPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Voltage_Subtract_YZ,
            'Title': None,
            'XAxisName': 'Voltage',
            'XUnit':"V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Voltage_Subtract_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['VoltageSubtractPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Voltage_Subtract_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Voltage',
            'YUnit': "V", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Voltage_Subtract_XZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['CurrentSubtractPlot'] = {
            'PlotObject': None, #Define in Setup2DPlot
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Current_Subtract_2DPlot,
            'Title': 'Current',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['CurrentSubtractPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Current_Subtract_YZ,
            'Title': None,
            'XAxisName': 'Current',
            'XUnit':"A",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Current_Subtract_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['CurrentSubtractPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Current_Subtract_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Current',
            'YUnit': "A", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Current_Subtract_XZLineCut,
            'Value': 0.0,
        }
        
        self.SetupPlots()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.pushButton_StartHysteresisSweep: (self.UpperLevel.DeviceList['DataAquisition_Device']['DeviceObject'] != False) and (self.UpperLevel.DeviceList['Hysteresis_Device']['DeviceObject'] != False) and self.UpperLevel.DEMONS.Scanning_Flag == False or True,
            self.pushButton_AbortHysteresisSweep: self.UpperLevel.DEMONS.Scanning_Flag == True,
            self.lineEdit_StartVoltage: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.lineEdit_EndVoltage: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.lineEdit_Numberofstep: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.lineEdit_Delay: self.UpperLevel.DEMONS.Scanning_Flag == False,
        }

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)

    def SetupPlots(self):
        for PlotName in self.Plotlist:
            Connect2DPlots(PlotName, self.Plotlist)
            
    @inlineCallbacks
    def StartMeasurement(self, c):
        try:
            self.UpperLevel.DEMONS.SetScanningFlag(True)
            self.UpperLevel.Refreshinterface()

            Multiplier = [self.UpperLevel.Parameter['Voltage_LI_Sensitivity'] * self.UpperLevel.Parameter['Voltage_LI_Gain'] / 10.0, self.UpperLevel.Parameter['Current_LI_Sensitivity'] * self.UpperLevel.Parameter['Current_LI_Gain'] / 10.0] #Voltage, Current

            ImageNumber, ImageDir = yield CreateDataVaultFile(self.UpperLevel.serversList['dv'], 'Gate Hysteresis Sweep ' + str(self.UpperLevel.Parameter['DeviceName']), ('Gate Index', 'Magnetic Field Index', 'Gate Voltage', 'Magnetic Field'), ('Voltage forth', 'Current forth', 'Resistance forth', 'Conductance forth', 'Voltage back', 'Current back', 'Resistance back', 'Conductance back', 'Voltage Subtract', 'Current Subtract', 'Resistance Subtract', 'Conductance Subtract'))
            self.UpperLevel.lineEdit_ImageNumber.setText(ImageNumber)
            self.UpperLevel.lineEdit_ImageDir.setText(ImageDir)

            yield AddParameterToDataVault(self.UpperLevel.serversList['dv'], self.UpperLevel.Parameter)
            ClearPlots(self.Plotlist)

            GateChannel, VoltageChannel, CurrentChannel = self.UpperLevel.Parameter['FourTerminal_GateChannel'], self.UpperLevel.Parameter['FourTerminal_VoltageReadingChannel'], self.UpperLevel.Parameter['FourTerminal_CurrentReadingChannel']
            StartField, EndField = self.UpperLevel.Parameter['Hysteresis_StartField'], self.UpperLevel.Parameter['Hysteresis_EndField']
            FieldSteps, FieldDelay = self.UpperLevel.Parameter['Hysteresis_Numberofstep'], self.UpperLevel.Parameter['Hysteresis_Delay']
            FieldSpeed = self.UpperLevel.Parameter['Hysteresis_RampSpeed']
            StartVoltage, EndVoltage = self.UpperLevel.Parameter['GateHysteresis_StartVoltage'], self.UpperLevel.Parameter['GateHysteresis_EndVoltage']
            NumberOfSteps, VoltageDelay = self.UpperLevel.Parameter['GateHysteresis_Numberofstep'], self.UpperLevel.Parameter['GateHysteresis_Delay']

            self.Data2D = np.zeros((FieldSteps * NumberOfSteps, 16)) #4 independent variables, 12 dependent variables
            FieldIndexData, VoltageIndexData = np.meshgrid(range(FieldSteps), range(NumberOfSteps)) #generate meshgrid of the index, look up np.meshgrid for example
            FieldValue, VoltageValue = np.meshgrid(np.linspace(StartField, EndField, FieldSteps), np.linspace(StartVoltage, EndVoltage, NumberOfSteps)) #generate meshgrid of the value, look up np.meshgrid for example
            
            self.Data2D[:, 0] = VoltageIndexData.flatten()
            self.Data2D[:, 1] = FieldIndexData.flatten()
            self.Data2D[:, 2] = VoltageValue.flatten()
            self.Data2D[:, 3] = FieldValue.flatten()
            
            for Plot in self.Plotlist:
                self.Plotlist[Plot]['PlotData'] = np.zeros((NumberOfSteps, FieldSteps))
                
            for VoltageIndex in range(NumberOfSteps):
                #Set Gate Voltage
                yield Ramp_DACADC(self.UpperLevel.DeviceList['DataAquisition_Device']['DeviceObject'], GateChannel, 0.0, np.linspace(StartVoltage, EndVoltage, NumberOfSteps)[VoltageIndex], 0.0001, 0.01) #Set the DAC to the correct voltage, hard coded how fast it sweep
                yield SleepAsync(self.reactor, VoltageDelay)
                
                for FieldIndex in range(FieldSteps):
                    if self.UpperLevel.DEMONS.Scanning_Flag == False:
                        print('Abort the Sweep')
                        yield self.FinishSweep()
                        break
                            
                    #Set Magnetic Field
                    # yield RampMagneticField(self.UpperLevel.DeviceList['Magnet_Device']['DeviceObject'], str(self.UpperLevel.DeviceList['Magnet_Device']['ComboBoxServer'].currentText()), MagneticFieldSet[FieldIndex], FieldSpeed, self.reactor)
                    yield SleepAsync(self.reactor, FieldDelay)
                    self.Data2D[FieldIndex][2] = yield Read_ADC(self.UpperLevel.DeviceList['DataAquisition_Device']['DeviceObject'], VoltageChannel) #Voltage
                    self.Data2D[FieldIndex][3] = yield Read_ADC(self.UpperLevel.DeviceList['DataAquisition_Device']['DeviceObject'], CurrentChannel) #Current
                    self.Data2D[FieldIndex][2: 4] = Multiply(self.Data2D[FieldIndex][2: 4], Multiplier) 
                    self.Data2D[FieldIndex][4] = Division(self.Data2D[FieldIndex][2], self.Data2D[FieldIndex][3]) #Resistance forth
                    self.Data2D[FieldIndex][5] = Division(self.Data2D[FieldIndex][3], self.Data2D[FieldIndex][2]) #Conductance forth
    
                    self.Plotlist['VoltagePlot']['PlotData Forth'][1] = self.Data2D[:,2]
                    self.Plotlist['CurrentPlot']['PlotData Forth'][1] = self.Data2D[:,3]
                    self.Plotlist['ResistancePlot']['PlotData Forth'][1] = self.Data2D[:,4]
    
                    ClearPlots(self.Plotlist)
                    for Plot in self.Plotlist:
                        Plot1DData(self.Plotlist[Plot]['PlotData Forth'][0], self.Plotlist[Plot]['PlotData Forth'][1], self.Plotlist[Plot]['PlotObject'], 'r')
                        Plot1DData(self.Plotlist[Plot]['PlotData Back'][0], self.Plotlist[Plot]['PlotData Back'][1], self.Plotlist[Plot]['PlotObject'], 'b')
                    
                for FieldIndex in reversed(range(FieldSteps)):
                    if self.UpperLevel.DEMONS.Scanning_Flag == False:
                        print('Abort the Sweep')
                        yield self.FinishSweep()
                        break
                    
                    #Set Magnetic Field
                    # yield RampMagneticField(self.UpperLevel.DeviceList['Magnet_Device']['DeviceObject'], str(self.UpperLevel.DeviceList['Magnet_Device']['ComboBoxServer'].currentText()), MagneticFieldSet[FieldIndex], FieldSpeed, self.reactor)
                    yield SleepAsync(self.reactor, FieldDelay)
                    self.Data2D[FieldIndex][6] = yield Read_ADC(self.UpperLevel.DeviceList['DataAquisition_Device']['DeviceObject'], VoltageChannel) #Voltage
                    self.Data2D[FieldIndex][7] = yield Read_ADC(self.UpperLevel.DeviceList['DataAquisition_Device']['DeviceObject'], CurrentChannel) #Current
                    self.Data2D[FieldIndex][6: 8] = Multiply(self.Data2D[FieldIndex][6: 8], Multiplier) 
                    self.Data2D[FieldIndex][8] = Division(self.Data2D[FieldIndex][6], self.Data2D[FieldIndex][7]) #Resistance forth
                    self.Data2D[FieldIndex][9] = Division(self.Data2D[FieldIndex][7], self.Data2D[FieldIndex][6]) #Conductance forth
                    
                    self.Plotlist['VoltagePlot']['PlotData Back'][1] = self.Data2D[:,6]
                    self.Plotlist['CurrentPlot']['PlotData Back'][1] = self.Data2D[:,7]
                    self.Plotlist['ResistancePlot']['PlotData Back'][1] = self.Data2D[:,8]
                    
                    ClearPlots(self.Plotlist)
                    for Plot in self.Plotlist:
                        Plot1DData(self.Plotlist[Plot]['PlotData Forth'][0], self.Plotlist[Plot]['PlotData Forth'][1], self.Plotlist[Plot]['PlotObject'], 'r')
                        Plot1DData(self.Plotlist[Plot]['PlotData Back'][0], self.Plotlist[Plot]['PlotData Back'][1], self.Plotlist[Plot]['PlotObject'], 'b')
                    
                    if FieldIndex == 0:
                        self.Data2D = Generate_Difference(self.Data2D, 2, 6, 10)
                        self.Data2D = Generate_Difference(self.Data2D, 3, 7, 11)
                        self.Data2D = Generate_Difference(self.Data2D, 4, 8, 12)
                        self.Data2D = Generate_Difference(self.Data2D, 5, 9, 13)
                        self.FinishSweep()


        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    @inlineCallbacks
    def FinishSweep(self):
        try:
            self.UpperLevel.serversList['dv'].add(self.Data2D)
            if self.checkBox_HysteresisSetting_BacktoZero.isChecked():
                yield SleepAsync(self.reactor, 1)
                # yield RampMagneticField(self.UpperLevel.DeviceList['Hysteresis_Device']['DeviceObject'], str(self.UpperLevel.DeviceList['Hysteresis_Device']['ComboBoxServer'].currentText()), 0.0, self.UpperLevel.Parameter['Hysteresis_RampSpeed'], self.reactor)
            self.UpperLevel.serversList['dv'].add_comment(str(self.UpperLevel.textEdit_Comment.toPlainText()))
            self.UpperLevel.DEMONS.SetScanningFlag(False)
            self.UpperLevel.Refreshinterface()
            saveDataToSessionFolder(self.winId(), self.UpperLevel.sessionFolder, str(self.UpperLevel.lineEdit_ImageNumber.text()) + ' - ' + 'Hysteresis ' + self.UpperLevel.Parameter['DeviceName'])
            saveDataToSessionFolder(self.UpperLevel.winId(), self.UpperLevel.sessionFolder, str(self.UpperLevel.lineEdit_ImageNumber.text()) + ' - ' + 'Four Terminal ' + self.UpperLevel.Parameter['DeviceName'])

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
