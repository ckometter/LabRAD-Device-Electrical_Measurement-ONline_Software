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
Ui_MagnetControlWindow, QtBaseClass = uic.loadUiType(os.path.join(path, "MagnetExtensionWindow.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

class MagnetControl(QtGui.QMainWindow, Ui_MagnetControlWindow):
    def __init__(self, reactor, UpperLevel, parent = None):
        super(MagnetControl, self).__init__(parent)

        self.reactor = reactor
        self.UpperLevel = UpperLevel
        self.parent = parent
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.comboBox_MagnetControl_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.UpperLevel.DeviceList, 'Magnet_Device', self.UpperLevel.serversList, str(self.UpperLevel.DeviceList['Magnet_Device']['ComboBoxServer'].currentText())))
        self.comboBox_MagnetControl_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.UpperLevel.DeviceList, 'Magnet_Device', str(self.UpperLevel.DeviceList['Magnet_Device']['ComboBoxDevice'].currentText()), self.UpperLevel.Refreshinterface))
        self.lineEdit_StartField.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'MagnetControl_StartField', self.UpperLevel.lineEdit))
        self.lineEdit_StartField.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'MagnetControl_Numberofstep', 'MagnetControl_EndField', 'MagnetControl_StartField', 'MagnetControl_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.lineEdit_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'MagnetControl_EndField', self.UpperLevel.lineEdit))
        self.lineEdit_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'MagnetControl_Numberofstep', 'MagnetControl_EndField', 'MagnetControl_StartField', 'MagnetControl_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.lineEdit_Numberofstep.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.UpperLevel.Parameter, 'MagnetControl_Numberofstep', 'MagnetControl_EndField', 'MagnetControl_StartField', 'MagnetControl_Numberofstep_Status', self.UpperLevel.lineEdit))
        self.pushButton_MagnetControl_NoSmTpTSwitch.clicked.connect(lambda: Toggle_NumberOfSteps_StepSize(self.UpperLevel.Parameter, 'MagnetControl_Numberofstep', 'MagnetControl_EndField', 'MagnetControl_StartField', 'MagnetControl_Numberofstep_Status', self.label_MangnetControl_NumberofStep, 'Tesla per Step', self.UpperLevel.lineEdit))  
        self.lineEdit_RampSpeed.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'MagnetControl_RampSpeed', self.UpperLevel.lineEdit))
        self.lineEdit_Delay.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.UpperLevel.Parameter, 'MagnetControl_Delay', self.UpperLevel.lineEdit))

        self.pushButton_StartFourTerminalSweep.clicked.connect(self.StartMeasurement)
        self.pushButton_AbortFourTerminalSweep.clicked.connect(lambda: self.UpperLevel.DEMONS.SetScanningFlag(False))

        self.Plotlist = {}
        self.Plotlist['ResistancePlot'] = {
            'PlotObject': None,
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Resistance_2DPlot,
            'Title': 'Resistance',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['ResistancePlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Resistance_YZ,
            'Title': None,
            'XAxisName': 'Resistance',
            'XUnit': u"\u03A9",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Resistance_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['ResistancePlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Resistance_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Resistance',
            'YUnit': u"\u03A9", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Resistance_XZLineCut,
            'Value': 0.0,
        }

        self.Plotlist['VoltagePlot'] = {
            'PlotObject': None,
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Voltage_2DPlot,
            'Title': 'Voltage',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        self.Plotlist['VoltagePlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Voltage_YZ,
            'Title': None,
            'XAxisName': 'Voltage',
            'XUnit':"V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Voltage_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['VoltagePlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Voltage_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Voltage',
            'YUnit': "V", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Voltage_XZLineCut,
            'Value': 0.0,
        }

        self.Plotlist['CurrentPlot'] = {
            'PlotObject': None, #Define in Setup2DPlot
            'PlotData': np.zeros((2, 2)), 
            'Layout': self.Layout_Current_2DPlot,
            'Title': 'Current',
            'XAxisName': 'Gate Voltage',
            'XUnit': "V",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T",
        }
        # self.Plotlist['CurrentPlot']['PlotObject'] = pg.ImageView(view = self.Plotlist['CurrentPlot']['PlotObject'])
        self.Plotlist['CurrentPlot']['YZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Current_YZ,
            'Title': None,
            'XAxisName': 'Current',
            'XUnit':"A",
            'YAxisName': 'Magnetic Field',
            'YUnit': "T", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 90, movable = True),
            'LineEdit': self.lineEdit_Current_YZLineCut,
            'Value': 0.0,
        }
        self.Plotlist['CurrentPlot']['XZPlot'] = {
            'PlotObject': pg.PlotWidget(parent = None),
            'PlotData': [[], []],
            'Layout': self.Layout_Current_XZ,
            'Title': None,
            'XAxisName': 'Gate Voltage',
            'XUnit':"V",
            'YAxisName': 'Current',
            'YUnit': "A", 
            'LineCut': pg.InfiniteLine(pos = 0, angle = 0, movable = True),
            'LineEdit': self.lineEdit_Current_XZLineCut,
            'Value': 0.0,
        }

        self.SetupPlots()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.pushButton_StartFourTerminalSweep: (self.UpperLevel.DeviceList['Magnet_Device']['DeviceObject'] != False) and self.UpperLevel.DEMONS.Scanning_Flag == False and self.UpperLevel.serversList['dv'] != False,
            self.pushButton_AbortFourTerminalSweep: self.UpperLevel.DEMONS.Scanning_Flag == True,
            self.comboBox_MagnetControl_SelectServer: self.UpperLevel.DEMONS.Scanning_Flag == False,
            self.comboBox_MagnetControl_SelectDevice: self.UpperLevel.DEMONS.Scanning_Flag == False,
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
            Connect2DPlots(PlotName, self.Plotlist)

    @inlineCallbacks
    def StartMeasurement(self, c):
        try:
            self.UpperLevel.DEMONS.SetScanningFlag(True)
            self.UpperLevel.Refreshinterface()

            Multiplier = [self.UpperLevel.Parameter['Voltage_LI_Sensitivity'] * self.UpperLevel.Parameter['Voltage_LI_Gain'] / 10.0, self.UpperLevel.Parameter['Current_LI_Sensitivity'] * self.UpperLevel.Parameter['Current_LI_Gain'] / 10.0] #Voltage, Current

            ImageNumber, ImageDir = yield CreateDataVaultFile(self.UpperLevel.serversList['dv'], 'Gate And Magnetic Field Sweep' + str(self.UpperLevel.Parameter['DeviceName']), ('Magnetic Field Index', 'Gate Index', 'Magnetic Field', 'Gate Voltage'), ('Voltage', 'Current', 'Resistance', 'Conductance'))
            self.UpperLevel.lineEdit_ImageNumber.setText(ImageNumber)
            self.UpperLevel.lineEdit_ImageDir.setText(ImageDir)

            yield AddParameterToDataVault(self.UpperLevel.serversList['dv'], self.UpperLevel.Parameter)
            ClearPlots(self.Plotlist)
            ClearPlots(self.UpperLevel.Plotlist)

            GateChannel, VoltageChannel, CurrentChannel = self.UpperLevel.Parameter['FourTerminal_GateChannel'], self.UpperLevel.Parameter['FourTerminal_VoltageReadingChannel'], self.UpperLevel.Parameter['FourTerminal_CurrentReadingChannel']
            StartVoltage, EndVoltage = self.UpperLevel.Parameter['FourTerminal_StartVoltage'], self.UpperLevel.Parameter['FourTerminal_EndVoltage']
            NumberOfSteps, Delay = self.UpperLevel.Parameter['FourTerminal_Numberofstep'], self.UpperLevel.Parameter['FourTerminal_Delay']
            StartField, EndField = self.UpperLevel.Parameter['MagnetControl_StartField'], self.UpperLevel.Parameter['MagnetControl_EndField']
            FieldSteps, FieldDelay = self.UpperLevel.Parameter['MagnetControl_Numberofstep'], self.UpperLevel.Parameter['MagnetControl_Delay']
            FieldSpeed = self.UpperLevel.Parameter['MagnetControl_RampSpeed']

            Data2D = np.empty((0, 8))

            for Plot in self.Plotlist:
                self.Plotlist[Plot]['PlotData'] = np.zeros((FieldSteps, NumberOfSteps))

            MagneticFieldSet = np.linspace(StartField, EndField, FieldSteps)
            for FieldIndex in range(FieldSteps):
                if self.UpperLevel.DEMONS.Scanning_Flag == False:
                    print('Abort the Sweep')
                    yield self.FinishSweep()
                    break

                #Set Magnetic Field
                yield RampMagneticField(self.UpperLevel.DeviceList['Magnet_Device']['DeviceObject'], str(self.UpperLevel.DeviceList['Magnet_Device']['ComboBoxServer'].currentText()), MagneticFieldSet[FieldIndex], FieldSpeed, self.reactor)
                yield SleepAsync(self.reactor, FieldDelay)

                #Ramp DACADC to initial
                yield Ramp_DACADC(self.UpperLevel.DeviceList['DataAquisition_Device']['DeviceObject'], GateChannel, 0.0, StartVoltage, self.UpperLevel.Parameter['Setting_RampStepSize'], self.UpperLevel.Parameter['Setting_RampDelay'])
                yield SleepAsync(self.reactor, self.UpperLevel.Parameter['Setting_WaitTime'])

                #Take Data
                Data1D = yield Buffer_Ramp_DACADC(self.UpperLevel.DeviceList['DataAquisition_Device']['DeviceObject'], [GateChannel], [VoltageChannel, CurrentChannel],[StartVoltage], [EndVoltage], NumberOfSteps, Delay)
                
                Data1D = Multiply(Data1D, Multiplier) #Scale them with corresponding multiplier [voltage, current]
                Data1D = AttachData_Front(Data1D, np.linspace(StartVoltage, EndVoltage, NumberOfSteps)) #Attach Gate Voltage
                Data1D = AttachData_Front(Data1D, np.linspace(MagneticFieldSet[FieldIndex], MagneticFieldSet[FieldIndex], NumberOfSteps)) #Attach Magnetic Field
                Data1D = AttachData_Front(Data1D, range(NumberOfSteps)) #Attach Gate Index
                Data1D = AttachData_Front(Data1D, np.linspace(FieldIndex, FieldIndex, NumberOfSteps)) #Attach Field Index
                Data1D = Attach_ResistanceConductance(Data1D, 4, 5)
                self.UpperLevel.serversList['dv'].add(Data1D)

                XData = np.linspace(StartVoltage, EndVoltage, NumberOfSteps)
                VoltageData, CurrentData, ResistanceData = Data1D[:, 4], Data1D[:, 5], Data1D[:, 6]
                ClearPlots(self.UpperLevel.Plotlist)
                Plot1DData(XData, VoltageData, self.UpperLevel.Plotlist['VoltagePlot']['PlotObject'])
                Plot1DData(XData, CurrentData, self.UpperLevel.Plotlist['CurrentPlot']['PlotObject'])
                Plot1DData(XData, ResistanceData, self.UpperLevel.Plotlist['ResistancePlot']['PlotObject'])

                #Sync Data2D
                Data2D = np.append(Data2D, Data1D, axis = 0)
                self.Plotlist['VoltagePlot']['PlotData'][FieldIndex] = VoltageData
                self.Plotlist['CurrentPlot']['PlotData'][FieldIndex] = CurrentData
                self.Plotlist['ResistancePlot']['PlotData'][FieldIndex] = ResistanceData

                MinGateVoltage, MinField = np.amin([StartVoltage, EndVoltage]), np.amin([StartField, EndField])
                ScaleGateVoltage, ScaleField = abs(StartVoltage - EndVoltage) / (NumberOfSteps - 1), abs(StartField - EndField) / (FieldSteps - 1)
                for PlotName in self.Plotlist:
                    Plot2DData(self.Plotlist[PlotName]['PlotObject'], self.Plotlist[PlotName]['PlotData'].T, MinGateVoltage, MinField, ScaleGateVoltage, ScaleField, autoRange = self.checkBox_AutoRange.isChecked(), autoLevels = self.checkBox_AutoLevel.isChecked())
                    RefreshLineCutPlot(self.Plotlist[PlotName], 'YZPlot', self.Plotlist[PlotName]['PlotData'])
                    RefreshLineCutPlot(self.Plotlist[PlotName], 'XZPlot', self.Plotlist[PlotName]['PlotData'])

                if FieldIndex == FieldSteps - 1:
                    yield self.FinishSweep()

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

    @inlineCallbacks
    def FinishSweep(self):
        try:
            if self.checkBox_FourTerminalMagneticFieldSetting_BacktoZero.isChecked():
                yield SleepAsync(self.reactor, 1)
                yield RampMagneticField(self.UpperLevel.DeviceList['Magnet_Device']['DeviceObject'], str(self.UpperLevel.DeviceList['Magnet_Device']['ComboBoxServer'].currentText()), 0.0, self.UpperLevel.Parameter['MagnetControl_RampSpeed'], self.reactor)
            self.UpperLevel.serversList['dv'].add_comment(str(self.UpperLevel.textEdit_Comment.toPlainText()))
            self.UpperLevel.DEMONS.SetScanningFlag(False)
            self.UpperLevel.Refreshinterface()
            saveDataToSessionFolder(self.winId(), self.UpperLevel.sessionFolder, str(self.UpperLevel.lineEdit_ImageNumber.text()) + ' - ' + 'Magnetic Field ' + self.UpperLevel.Parameter['DeviceName'])
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
