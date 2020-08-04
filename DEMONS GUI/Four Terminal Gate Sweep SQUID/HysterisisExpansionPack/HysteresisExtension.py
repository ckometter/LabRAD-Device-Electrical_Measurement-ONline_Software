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
Ui_HysteresisWindow, QtBaseClass = uic.loadUiType(os.path.join(path, "HysteresisExtensionWindow.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

class Hysteresis(QtGui.QMainWindow, Ui_HysteresisWindow):
    def __init__(self, reactor, UpperLevel, parent = None):
        super(Hysteresis, self).__init__(parent)

        self.reactor = reactor
        self.UpperLevel = UpperLevel
        self.parent = parent
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.comboBox_Hysteresis_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.UpperLevel.DeviceList, 'Hysteresis_Device', self.UpperLevel.serversList, str(self.UpperLevel.DeviceList['Hysteresis_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Hysteresis_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.UpperLevel.DeviceList, 'Hysteresis_Device', str(self.UpperLevel.DeviceList['Hysteresis_Device']['ComboBoxDevice'].currentText()), self.UpperLevel.Refreshinterface))
        self.lineEdit_StartField.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'Hysteresis_StartField', self.UpperLevel.lineEdit))
        self.lineEdit_StartField.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'Hysteresis_Numberofstep', 'Hysteresis_EndField', 'Hysteresis_StartField', 'Hysteresis_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.lineEdit_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'Hysteresis_EndField', self.UpperLevel.lineEdit))
        self.lineEdit_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'Hysteresis_Numberofstep', 'Hysteresis_EndField', 'Hysteresis_StartField', 'Hysteresis_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.lineEdit_Numberofstep.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'Hysteresis_Numberofstep', 'Hysteresis_EndField', 'Hysteresis_StartField', 'Hysteresis_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.pushButton_Hysteresis_NoSmTpTSwitch.clicked.connect(lambda: Toggle_NumberOfSteps_StepSize(self.UpperLevel.Parameter, 'Hysteresis_Numberofstep', 'Hysteresis_EndField', 'Hysteresis_StartField', 'Hysteresis_Numberofstep_Status', self.label_Hysteresis_NumberofStep, 'Tesla per Step', self.UpperLevel.lineEdit))  
        self.lineEdit_RampSpeed.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'Hysteresis_RampSpeed', self.UpperLevel.lineEdit))
        self.lineEdit_Delay.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'Hysteresis_Delay', self.UpperLevel.lineEdit))

        self.pushButton_StartHysteresisSweep.clicked.connect(self.StartMeasurement)
        self.pushButton_AbortHysteresisSweep.clicked.connect(lambda: self.UpperLevel.DEMONS.SetScanningFlag(False))

        self.Plotlist = {}
        self.Plotlist['VoltagePlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData Forth': [[], []],
            'PlotData Back': [[], []],
            'Layout': self.Layout_HysteresislPlot_1,
            'Title': 'Voltage',
            'XAxisName': 'Magnetic Field',
            'XUnit':"T",
            'YAxisName': 'Voltage',
            'YUnit': "V",
        }
        self.Plotlist['CurrentPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData Forth': [[], []],
            'PlotData Back': [[], []],
            'Layout': self.Layout_HysteresislPlot_2,
            'Title': 'Current',
            'XAxisName': 'Magnetic Field',
            'XUnit':"T",
            'YAxisName': 'Current',
            'YUnit': "A",
        }
        self.Plotlist['ResistancePlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData Forth': [[], []],
            'PlotData Back': [[], []],
            'Layout': self.Layout_HysteresislPlot_3,
            'Title': 'Resistance',
            'XAxisName': 'Magnetic Field',
            'XUnit':"T",
            'YAxisName': 'Resistance',
            'YUnit': u"\u03A9", #Capital Ohm 
		}			
		
        self.SetupPlots()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.pushButton_StartHysteresisSweep: (self.UpperLevel.DeviceList['Hysteresis_Device']['DeviceObject'] != False) and self.UpperLevel.DEMONS.Scanning_Flag == False and self.UpperLevel.serversList['dv'] != False,
            self.pushButton_AbortHysteresisSweep: self.UpperLevel.DEMONS.Scanning_Flag == True,
            self.comboBox_Hysteresis_SelectServer: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.comboBox_Hysteresis_SelectDevice: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.lineEdit_StartField: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.lineEdit_EndVoltage: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.lineEdit_Numberofstep: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.lineEdit_RampSpeed: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.lineEdit_Delay: self.UpperLevel.DEMONS.Scanning_Flag == False,
        }

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)

    def SetupPlots(self):
        for PlotName in self.Plotlist:
            Setup1DPlot(self.Plotlist[PlotName]['PlotObject'], self.Plotlist[PlotName]['Layout'], self.Plotlist[PlotName]['Title'], self.Plotlist[PlotName]['YAxisName'], self.Plotlist[PlotName]['YUnit'], self.Plotlist[PlotName]['XAxisName'], self.Plotlist[PlotName]['XUnit'])#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

    @inlineCallbacks
    def StartMeasurement(self, c):
        try:
            self.UpperLevel.DEMONS.SetScanningFlag(True)
            self.UpperLevel.Refreshinterface()

            Multiplier = [self.UpperLevel.Parameter['Voltage_LI_Sensitivity'] * self.UpperLevel.Parameter['Voltage_LI_Gain'] / 10.0, self.UpperLevel.Parameter['Current_LI_Sensitivity'] * self.UpperLevel.Parameter['Current_LI_Gain'] / 10.0] #Voltage, Current

            ImageNumber, ImageDir = yield CreateDataVaultFile(self.UpperLevel.serversList['dv'], 'Hysteresis Sweep ' + str(self.UpperLevel.Parameter['DeviceName']), ('Magnetic Field Index', 'Magnetic Field'), ('Voltage forth', 'Current forth', 'Resistance forth', 'Conductance forth', 'Voltage back', 'Current back', 'Resistance back', 'Conductance back', 'Voltage Subtract', 'Current Subtract', 'Resistance Subtract', 'Conductance Subtract'))
            self.UpperLevel.lineEdit_ImageNumber.setText(ImageNumber)
            self.UpperLevel.lineEdit_ImageDir.setText(ImageDir)

            yield AddParameterToDataVault(self.UpperLevel.serversList['dv'], self.UpperLevel.Parameter)
            ClearPlots(self.Plotlist)

            GateChannel, VoltageChannel, CurrentChannel = self.UpperLevel.Parameter['FourTerminal_GateChannel'], self.UpperLevel.Parameter['FourTerminal_VoltageReadingChannel'], self.UpperLevel.Parameter['FourTerminal_CurrentReadingChannel']
            StartField, EndField = self.UpperLevel.Parameter['Hysteresis_StartField'], self.UpperLevel.Parameter['Hysteresis_EndField']
            FieldSteps, FieldDelay = self.UpperLevel.Parameter['Hysteresis_Numberofstep'], self.UpperLevel.Parameter['Hysteresis_Delay']
            FieldSpeed = self.UpperLevel.Parameter['Hysteresis_RampSpeed']

            self.Data2D = np.zeros((FieldSteps, 14)) #2 independent variables, 12 dependent variables
            self.Data2D[:, 0] = range(FieldSteps)# magnetic field index
            MagneticFieldSet = np.linspace(StartField, EndField, FieldSteps)
            self.Data2D[:, 1] = MagneticFieldSet # magnetic field 
            
            for Plot in self.Plotlist:
                self.Plotlist[Plot]['PlotData Forth'][0] = MagneticFieldSet
                self.Plotlist[Plot]['PlotData Forth'][1] = np.linspace(0.0, 0.0, FieldSteps)
                self.Plotlist[Plot]['PlotData Back'][0] = MagneticFieldSet
                self.Plotlist[Plot]['PlotData Back'][1] = np.linspace(0.0, 0.0, FieldSteps)
                
            
            for FieldIndex in range(FieldSteps):
                if self.UpperLevel.DEMONS.Scanning_Flag == False:
                    print('Abort the Sweep')
                    yield self.FinishSweep()
                    break
                        
                #Set Magnetic Field
                yield RampMagneticField(self.UpperLevel.DeviceList['Magnet_Device']['DeviceObject'], str(self.UpperLevel.DeviceList['Magnet_Device']['ComboBoxServer'].currentText()), MagneticFieldSet[FieldIndex], FieldSpeed, self.reactor)
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
                yield RampMagneticField(self.UpperLevel.DeviceList['Magnet_Device']['DeviceObject'], str(self.UpperLevel.DeviceList['Magnet_Device']['ComboBoxServer'].currentText()), MagneticFieldSet[FieldIndex], FieldSpeed, self.reactor)
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
                yield RampMagneticField(self.UpperLevel.DeviceList['Hysteresis_Device']['DeviceObject'], str(self.UpperLevel.DeviceList['Hysteresis_Device']['ComboBoxServer'].currentText()), 0.0, self.UpperLevel.Parameter['Hysteresis_RampSpeed'], self.reactor)
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
