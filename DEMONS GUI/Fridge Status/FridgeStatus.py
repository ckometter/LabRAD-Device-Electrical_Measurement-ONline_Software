from __future__ import division
import sys
import os
import twisted
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
from PyQt5 import Qt, QtGui, QtCore, uic
import pyqtgraph as pg
import numpy as np
#import exceptions
import time
import threading
import copy
from scipy.signal import detrend
from datetime import datetime, date

#importing a bunch of stuff
WAIT_TIME = 1.5 # waittime in s

path = os.path.dirname(os.path.realpath(__file__))
FridgeStatusUI, QtBaseClass = uic.loadUiType(os.path.join(path, "FridgeStatus.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

#Not required, but strongly ecommended functions used to format numbers in a particular way.
#sys.path.append(sys.path[0]+'\Resources')
from DEMONSFormat import *


class Window(QtGui.QMainWindow, FridgeStatusUI):

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)
        self.scanningflag = False
        self.tempDV = False
        self.pushButton_Servers.clicked.connect(self.showServersList)
        self.localcxn = False
        self.dv = False
        self.dvfolder = False
        self.osDVFolder = False

        self.SingleAxisMagX = False
        self.SingleAxisMagY = False
        self.SingleAxisMagZ = False
        self.SingleAxisContsRead = False
        self.ContsLMflag = False
        self.dv_lm = None
        self.serversList = { #Dictionary including toplevel server received from labrad connect
            'Lakeshore': False,
            'AMI430_X': False,
            'AMI430_Y': False,
            'AMI430_Z': False,
            'Levelmeter': False,
        }

        self.SOCKET_DICT = {
            'X':'he-3-cryostat GPIB Bus - TCPIP0::169.254.129.190::7180::SOCKET',
            'Y':'he-3-cryostat GPIB Bus - TCPIP0::169.254.246.230::7180::SOCKET',
            'Z': 'he-3-cryostat GPIB Bus - TCPIP0::169.254.193.6::7180::SOCKET'



        }
        self.DeviceList = {}#self.DeviceList['Device Name'][Device Property]

        self.DeviceList['Lakeshore_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Lakeshore_SelectServer,
            'ComboBoxDevice': self.comboBox_Lakeshore_SelectDevice,
            'ServerIndicator': self.pushButton_Lakeshore_ServerIndicator,
            'DeviceIndicator': self.pushButton_Lakeshore_DeviceIndicator,            
            'ServerNeeded': ['Lakeshore'],
        }
        self.DeviceList['MagnetX_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_MagnetX_SelectServer,
            'ComboBoxDevice': self.comboBox_MagnetX_SelectDevice,
            'ServerIndicator': self.pushButton_MagnetX_ServerIndicator,
            'DeviceIndicator': self.pushButton_MagnetX_DeviceIndicator,
            'ServerNeeded':['AMI430_X']
        }

        self.DeviceList['MagnetY_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_MagnetY_SelectServer,
            'ComboBoxDevice': self.comboBox_MagnetY_SelectDevice,
            'ServerIndicator': self.pushButton_MagnetY_ServerIndicator,
            'DeviceIndicator': self.pushButton_MagnetY_DeviceIndicator,
            'ServerNeeded':['AMI430_Y']
        }

        self.DeviceList['MagnetZ_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_MagnetZ_SelectServer,
            'ComboBoxDevice': self.comboBox_MagnetZ_SelectDevice,
            'ServerIndicator': self.pushButton_MagnetZ_ServerIndicator,
            'DeviceIndicator': self.pushButton_MagnetZ_DeviceIndicator,
            'ServerNeeded':['AMI430_Z']
        }

        self.DeviceList['Levelmeter'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Levelmeter_SelectServer,
            'ComboBoxDevice': self.comboBox_Levelmeter_SelectDevice,
            'ServerIndicator': self.pushButton_Levelmeter_ServerIndicator,
            'DeviceIndicator': self.pushButton_Levelmeter_DeviceIndicator,
            'ServerNeeded': ['Levelmeter']
        }

        self.targetnumber = {
            'RampRate1': 0.0,
            'RampRate2': 0.0,
            'HeaterRng1': 0,
            'HeaterRng2': 0,
            'Setpoint1': 0.0,
            'Setpoint2': 0.0,
            
        }


         
        self.outputParams = {

            'RampRate1': self.lineEdit_RampRate_1,
            'RampRate2': self.lineEdit_RampRate_2,
            'HeaterRng1': self.comboBox_HeaterRng1,
            'HeaterRng2': self.comboBox_HeaterRng2,
            'Setpoint1': self.lineEdit_Setpoint_1,
            'Setpoint2': self.lineEdit_Setpoint_2,

        }

        self.Labels = [
            self.label_Temp1,
            self.label_Temp2,
            self.label_Temp3,
            self.label_Temp4,
            self.label_Setpoint1,
            self.label_Setpoint2,
            self.label_HeaterOut1,
            self.label_HeaterOut2,
            self.label_HeaterRng1,
            self.label_HeaterRng2,
        ]

        self.magtargetnumberX = {
            'Target' : 0.0,
            'FieldRate': 0.0,
            'Max_Field': 1.2,
            'Max_Ramp_Rate': .25
        }
        self.magoutputParamsX = {
            'Target':self.lineEdit_TargetFieldX,
            'FieldRate':self.lineEdit_FieldRateX
        }
        self.magLabelsX = [
            self.label_FieldX,
            self.label_RateX,
            self.label_TargetFieldX,
            self.label_StatusX,
            self.label_PersSwitchX,
            self.label_PersModeX,
        ]

        self.magtargetnumberY = {
            'Target' : 0.0,
            'FieldRate': 0.0,
            'Max_Field': 1.2,
            'Max_Ramp_Rate': .25
        }

        self.magoutputParamsY = {
            'Target':self.lineEdit_TargetFieldY,
            'FieldRate':self.lineEdit_FieldRateY
        }

        self.magLabelsY = [
            self.label_FieldY,
            self.label_RateY,
            self.label_TargetFieldY,
            self.label_StatusY,
            self.label_PersSwitchY,
            self.label_PersModeY,
        ]

        self.magtargetnumberZ = {
            'Target' : 0.0,
            'FieldRate': 0.0,
            'Max_Field': 8.2,
            'Max_Ramp_Rate': 0.5,
        }


        self.magoutputParamsZ = {
            'Target':self.lineEdit_TargetFieldZ,
            'FieldRate':self.lineEdit_FieldRateZ
        }

        self.magLabelsZ = [
            self.label_FieldZ,
            self.label_RateZ,
            self.label_TargetFieldZ,
            self.label_StatusZ,
            self.label_PersSwitchZ,
            self.label_PersModeZ,
        ]

        self.LMLabels = [
            self.label_LMPercent,
            self.label_LMTimestamp,
        ]

        self.DetermineEnableConditions()

        self.comboBox_Lakeshore_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Lakeshore_Device', self.serversList, str(self.DeviceList['Lakeshore_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Lakeshore_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Lakeshore_Device', str(self.DeviceList['Lakeshore_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))

        self.comboBox_MagnetX_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'MagnetX_Device', self.serversList, str(self.DeviceList['MagnetX_Device']['ComboBoxServer'].currentText()),default_item = self.SOCKET_DICT['X']))
        self.comboBox_MagnetX_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'MagnetX_Device', str(self.DeviceList['MagnetX_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))

        self.comboBox_MagnetY_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'MagnetY_Device', self.serversList, str(self.DeviceList['MagnetY_Device']['ComboBoxServer'].currentText()),default_item = self.SOCKET_DICT['Y']))
        self.comboBox_MagnetY_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'MagnetY_Device', str(self.DeviceList['MagnetY_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))

        self.comboBox_MagnetZ_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'MagnetZ_Device', self.serversList, str(self.DeviceList['MagnetZ_Device']['ComboBoxServer'].currentText()),default_item = self.SOCKET_DICT['Z']))
        self.comboBox_MagnetZ_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'MagnetZ_Device', str(self.DeviceList['MagnetZ_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))

        self.comboBox_Levelmeter_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Levelmeter', self.serversList, str(self.DeviceList['Levelmeter']['ComboBoxServer'].currentText())))
        self.comboBox_Levelmeter_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Levelmeter', str(self.DeviceList['Levelmeter']['ComboBoxDevice'].currentText()), self.Refreshinterface))


        self.lineEdit_Setpoint_1.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.targetnumber, 'Setpoint1', self.outputParams, [0, 300.0]))
        self.lineEdit_Setpoint_2.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.targetnumber, 'Setpoint2', self.outputParams, [0, 300.0]))

        self.lineEdit_RampRate_1.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.targetnumber, 'RampRate1', self.outputParams, [0, 1000]))
        self.lineEdit_RampRate_2.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.targetnumber, 'RampRate2', self.outputParams, [0, 1000]))

        self.comboBox_HeaterRng1.currentIndexChanged.connect(lambda: UpdateComboBox(self.targetnumber,'HeaterRng1',self.outputParams))
        self.comboBox_HeaterRng2.currentIndexChanged.connect(lambda: UpdateComboBox(self.targetnumber,'HeaterRng2',self.outputParams))

        self.pushButton_ConnectDV.clicked.connect(lambda: createDVClient(self, self.localcxn))
        self.checkBox_TempDV.stateChanged.connect(lambda: self.setDV(self.checkBox_TempDV.isChecked()))

        self.pushButton_STARTRAMP.clicked.connect(lambda: Set_Lakeshore_Ramping(self.DeviceList['Lakeshore_Device']['DeviceObject'],np.reshape(list(self.targetnumber.values()),(3,2)) ))
        self.pushButton_READALL.clicked.connect(lambda: Read_Lakeshore_Status_SetLabel(self.DeviceList['Lakeshore_Device']['DeviceObject'],self.Labels))
        self.pushButton_CONTS.clicked.connect(lambda: self.startContsMeasurement([1,3],self.tempDV))
        self.pushButton_STOP.clicked.connect(lambda: self.endContsMeasurement())


        self.lineEdit_TargetFieldX.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.magtargetnumberX,'Target',self.magoutputParamsX,[-1*self.magtargetnumberX['Max_Field'],self.magtargetnumberX['Max_Field']]))
        self.lineEdit_FieldRateX.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.magtargetnumberX,'FieldRate',self.magoutputParamsX,[0.0,self.magtargetnumberX['Max_Ramp_Rate']]))
        
        self.pushButton_SetMagX.clicked.connect(lambda: Set_AMI(self.DeviceList['MagnetX_Device']['DeviceObject'],self.magtargetnumberX))
        self.pushButton_PauseMagX.clicked.connect(lambda: Pause_AMI(self.DeviceList['MagnetX_Device']['DeviceObject']))
        self.pushButton_ZeroMagX.clicked.connect(lambda: Zero_AMI(self.DeviceList['MagnetX_Device']['DeviceObject']))
        self.pushButton_ReadMagX.clicked.connect(lambda: Read_AMI_Status_SetLabel(self.DeviceList['MagnetX_Device']['DeviceObject'],self.magLabelsX))
        self.pushButton_RampMagX.clicked.connect(lambda: Ramp_AMI(self.DeviceList['MagnetX_Device']['DeviceObject']))
        self.pushButton_ReadMagContsX.clicked.connect(lambda: self.startContsMagXMeasurement())
        self.pushButton_EnterPersX.clicked.connect(lambda: Enter_PMode_AMI(self.DeviceList['MagnetX_Device']['DeviceObject']))
        self.pushButton_ExitPersX.clicked.connect(lambda: Exit_PMode_AMI(self.DeviceList['MagnetX_Device']['DeviceObject']))

        self.pushButton_EnableMagX.clicked.connect(lambda: self.ToggleSingleAxisX())

        self.lineEdit_TargetFieldY.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.magtargetnumberY,'Target',self.magoutputParamsY,[-1*self.magtargetnumberY['Max_Field'],self.magtargetnumberY['Max_Field']]))
        self.lineEdit_FieldRateY.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.magtargetnumberY,'FieldRate',self.magoutputParamsY,[0.0,self.magtargetnumberY['Max_Ramp_Rate']]))
        
        self.pushButton_SetMagY.clicked.connect(lambda: Set_AMI(self.DeviceList['MagnetY_Device']['DeviceObject'],self.magtargetnumberY))
        self.pushButton_PauseMagY.clicked.connect(lambda: Pause_AMI(self.DeviceList['MagnetY_Device']['DeviceObject']))
        self.pushButton_ZeroMagY.clicked.connect(lambda: Zero_AMI(self.DeviceList['MagnetY_Device']['DeviceObject']))
        self.pushButton_ReadMagY.clicked.connect(lambda: Read_AMI_Status_SetLabel(self.DeviceList['MagnetY_Device']['DeviceObject'],self.magLabelsY))
        self.pushButton_RampMagY.clicked.connect(lambda: Ramp_AMI(self.DeviceList['MagnetY_Device']['DeviceObject']))
        self.pushButton_ReadMagContsY.clicked.connect(lambda: self.startContsMagYMeasurement())
        self.pushButton_EnterPersY.clicked.connect(lambda: Enter_PMode_AMI(self.DeviceList['MagnetY_Device']['DeviceObject']))
        self.pushButton_ExitPersY.clicked.connect(lambda: Exit_PMode_AMI(self.DeviceList['MagnetY_Device']['DeviceObject']))

        self.pushButton_EnableMagY.clicked.connect(lambda: self.ToggleSingleAxisY())

        self.lineEdit_TargetFieldZ.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.magtargetnumberZ,'Target',self.magoutputParamsZ,[-1*self.magtargetnumberZ['Max_Field'],self.magtargetnumberZ['Max_Field']]))
        self.lineEdit_FieldRateZ.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.magtargetnumberZ,'FieldRate',self.magoutputParamsZ,[0.0,self.magtargetnumberZ['Max_Ramp_Rate']]))
        
        self.pushButton_SetMagZ.clicked.connect(lambda: Set_AMI(self.DeviceList['MagnetZ_Device']['DeviceObject'],self.magtargetnumberZ))
        self.pushButton_PauseMagZ.clicked.connect(lambda: Pause_AMI(self.DeviceList['MagnetZ_Device']['DeviceObject']))
        self.pushButton_ZeroMagZ.clicked.connect(lambda: Zero_AMI(self.DeviceList['MagnetZ_Device']['DeviceObject']))
        self.pushButton_ReadMagZ.clicked.connect(lambda: Read_AMI_Status_SetLabel(self.DeviceList['MagnetZ_Device']['DeviceObject'],self.magLabelsZ))
        self.pushButton_RampMagZ.clicked.connect(lambda: Ramp_AMI(self.DeviceList['MagnetZ_Device']['DeviceObject']))
        self.pushButton_ReadMagContsZ.clicked.connect(lambda: self.startContsMagZMeasurement())
        self.pushButton_EnterPersZ.clicked.connect(lambda: Enter_PMode_AMI(self.DeviceList['MagnetZ_Device']['DeviceObject']))
        self.pushButton_ExitPersZ.clicked.connect(lambda: Exit_PMode_AMI(self.DeviceList['MagnetZ_Device']['DeviceObject']))

        self.pushButton_EnableMagZ.clicked.connect(lambda: self.ToggleSingleAxisZ())


        self.pushButton_LMPing.clicked.connect(lambda: PingLM(self.DeviceList['Levelmeter']['DeviceObject'],self.LMLabels,self.reactor))
        self.pushButton_LMReadConts.clicked.connect(lambda: self.ContsLM())

        self.Refreshinterface()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.pushButton_STARTRAMP: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            self.pushButton_READALL: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            self.pushButton_CONTS: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            self.pushButton_STOP:  not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            #self.pushButton_ReadMagX: not self.SingleAxisMagX== False,
            self.pushButton_RampMagX: not self.SingleAxisMagX== False,
            self.pushButton_PauseMagX:not self.SingleAxisMagX == False,
            self.pushButton_SetMagX:not self.SingleAxisMagX == False,
            self.pushButton_ZeroMagX:not self.SingleAxisMagX== False,
            self.pushButton_EnterPersX: not self.SingleAxisMagX == False,
            self.pushButton_ExitPersX: not self.SingleAxisMagX == False,
            #self.pushButton_ReadMagContsX: not self.SingleAxisMagX == False,
            self.pushButton_EnableMagX: (not self.DeviceList['MagnetX_Device']['DeviceObject'] == False) and self.SingleAxisMagY == False and self.SingleAxisMagZ==False,
            
            #self.pushButton_ReadMagY: not self.SingleAxisMagY== False,
            self.pushButton_RampMagY: not self.SingleAxisMagY== False,
            self.pushButton_PauseMagY:not self.SingleAxisMagY == False,
            self.pushButton_SetMagY:not self.SingleAxisMagY == False,
            self.pushButton_ZeroMagY:not self.SingleAxisMagY== False,
            self.pushButton_EnterPersY: not self.SingleAxisMagY == False,
            self.pushButton_ExitPersY: not self.SingleAxisMagY == False,
            #self.pushButton_ReadMagContsY: not self.SingleAxisMagY == False,
            self.pushButton_EnableMagY:(not self.DeviceList['MagnetY_Device']['DeviceObject'] == False) and self.SingleAxisMagX == False and self.SingleAxisMagZ==False,
            
            #self.pushButton_ReadMagY: not self.SingleAxisMagY== False,
            self.pushButton_RampMagZ: not self.SingleAxisMagZ== False,
            self.pushButton_PauseMagZ:not self.SingleAxisMagZ == False,
            self.pushButton_SetMagZ:not self.SingleAxisMagZ == False,
            self.pushButton_ZeroMagZ:not self.SingleAxisMagZ== False,
            self.pushButton_EnterPersZ: not self.SingleAxisMagZ == False,
            self.pushButton_ExitPersZ: not self.SingleAxisMagZ == False,
            #self.pushButton_ReadMagContsY: not self.SingleAxisMagY == False,
            self.pushButton_EnableMagZ:(not self.DeviceList['MagnetZ_Device']['DeviceObject'] == False) and self.SingleAxisMagX == False and self.SingleAxisMagY ==False,



            #self.pushButton_SET_1: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            #self.pushButton_SET_2: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            #self.pushButton_SET_3: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            #self.pushButton_SET_4: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            #self.pushButton_Read_1: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            #self.pushButton_Read_2: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            #self.pushButton_Read_3: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
            #self.pushButton_Read_4: not self.DeviceList['Lakeshore_Device']['DeviceObject'] == False,
        }

    @inlineCallbacks
    def startContsMeasurement(self,channelList,DV):
        self.scanningflag = True
        t0 = time.time()
        #ClearPlots(self.Plotlist)
        # self.Plotlist['TempPlot'] = {
        #     'PlotObject': pg.PlotWidget(parent = None),
        #     'PlotData': [[],[],[]], # can plot 2 temp lines against time
        #     'Layout': self.Layout_FridgeStatusPlot1,
        #     'Title': 'Temperature',
        #     'XAxisName': 'Time',
        #     'XUnit': "s",
        #     'YAxisName': 'Temperature',
        #     'YUnit': "K"
        # }

        # self.SetupPlots()
        #create dv file if box is checked
        if DV:
            starttime = time.asctime(time.localtime(t0))
            ImageNumber, ImageDir = yield CreateDataVaultFile(self.dv,'FridgeStatus_Temperature '+str(starttime), ('t'),('T1','T2','T3','T4'))
        tlist = []
        counter = 0
        while self.scanningflag:
            data = yield Read_Lakeshore_Status_SetLabel(self.DeviceList['Lakeshore_Device']['DeviceObject'],self.Labels)
            tm = time.time()
            #self.Plotlist['TempPlot']['PlotData'][0].append(tm - t0)
            #self.Plotlist['TempPlot']['PlotData'][1].append(float(data[int(channelList[0])-1]))
            #self.Plotlist['TempPlot']['PlotData'][2].append(float(data[int(channelList[1])-1]))
            if DV:
                DataLine = np.array([tm-t0,float(data[0]),float(data[1]),float(data[2]),float(data[3])])
                yield self.dv.add(DataLine.T)
            #for i in range(0,len(channelList)):
                #Plot1DData(self.Plotlist['TempPlot']['PlotData'][0],self.Plotlist['TempPlot']['PlotData'][i+1], self.Plotlist['TempPlot']['PlotObject'], color = (i,len(channelList)), name = str('Channel '+str(channelList[i])),init = counter)
            yield SleepAsync(self.reactor, 3) #wait 3 seconds
            counter += 1

    def endContsMeasurement(self):
        self.scanningflag = False

    def ToggleSingleAxisX(self):
        if self.SingleAxisMagX == False:
            self.SingleAxisMagX = True
            setIndicator(self.pushButton_EnableMagX,'rgb(0,170,0)')
        elif self.SingleAxisMagX == True:
            self.SingleAxisMagX = False
            setIndicator(self.pushButton_EnableMagX,'rgb(161,0,0)')
        self.refreshServerIndicator()

    def ToggleSingleAxisY(self):
        if self.SingleAxisMagY == False:
            self.SingleAxisMagY = True
            setIndicator(self.pushButton_EnableMagY,'rgb(0,170,0)')
        elif self.SingleAxisMagY == True:
            self.SingleAxisMagY = False
            setIndicator(self.pushButton_EnableMagY,'rgb(161,0,0)')
        self.refreshServerIndicator()

    def ToggleSingleAxisZ(self):
        print(self.serversList)
        print(self.DeviceList)
        if self.SingleAxisMagZ == False:
            self.SingleAxisMagZ = True
            setIndicator(self.pushButton_EnableMagZ,'rgb(0,170,0)')
        elif self.SingleAxisMagZ == True:
            self.SingleAxisMagZ = False
            setIndicator(self.pushButton_EnableMagZ,'rgb(161,0,0)')
        self.refreshServerIndicator()
    @inlineCallbacks
    def startContsMagXMeasurement(self):
        if self.SingleAxisContsRead == False:
            self.SingleAxisContsRead = True
            print(self.DeviceList['MagnetX_Device']['DeviceObject'])
            setIndicator(self.pushButton_ReadMagContsX,'rgb(0,170,0)')
            while self.SingleAxisContsRead:
                yield Read_AMI_Status_SetLabel(self.DeviceList['MagnetX_Device']['DeviceObject'],self.magLabelsX)
                yield SleepAsync(self.reactor,WAIT_TIME) #wait 3 seconds
        elif self.SingleAxisContsRead == True:
            self.SingleAxisContsRead = False
            setIndicator(self.pushButton_ReadMagContsX,'rgb(161,0,0)')

    @inlineCallbacks
    def startContsMagYMeasurement(self):
        if self.SingleAxisContsRead == False:
            print(self.DeviceList['MagnetY_Device']['DeviceObject'])

            self.SingleAxisContsRead = True
            setIndicator(self.pushButton_ReadMagContsY,'rgb(0,170,0)')
            while self.SingleAxisContsRead:
                yield Read_AMI_Status_SetLabel(self.DeviceList['MagnetY_Device']['DeviceObject'],self.magLabelsY)
                yield SleepAsync(self.reactor,WAIT_TIME) #wait 3 seconds
        elif self.SingleAxisContsRead == True:
            self.SingleAxisContsRead = False
            setIndicator(self.pushButton_ReadMagContsY,'rgb(161,0,0)')

    @inlineCallbacks
    def startContsMagZMeasurement(self):
        if self.SingleAxisContsRead == False:
            print(self.DeviceList['MagnetZ_Device']['DeviceObject'])

            self.SingleAxisContsRead = True
            setIndicator(self.pushButton_ReadMagContsZ,'rgb(0,170,0)')
            while self.SingleAxisContsRead:
                yield Read_AMI_Status_SetLabel(self.DeviceList['MagnetZ_Device']['DeviceObject'],self.magLabelsZ)
                yield SleepAsync(self.reactor,WAIT_TIME) #wait 3 seconds
        elif self.SingleAxisContsRead == True:
            self.SingleAxisContsRead = False
            setIndicator(self.pushButton_ReadMagContsZ,'rgb(161,0,0)')


    @inlineCallbacks
    def ContsLM(self):
        if self.ContsLMflag == False:
            self.ContsLMflag = True
            setIndicator(self.pushButton_LMReadConts,'rgb(0,170,0)')
            data_dir = 'he_level'
            if self.dv_lm is None:
                from labrad.wrappers import connectAsync
                cxn_lm = yield connectAsync(host = '127.0.0.1', password='sSET2018')
                self.dv_lm = cxn_lm.data_vault()
            try:
                wait_time = float(self.LMWaitTime.currentText())
            except:
                wait_time = 1800
            dv_number = create_file_LM(self.dv_lm,data_dir)
            while self.ContsLMflag:
                yield PingLM(self.DeviceList['Levelmeter']['DeviceObject'],self.LMLabels,self.reactor) 
                yield SleepAsync(self.reactor, wait_time)        
        elif self.ContsLMflag == True:
            self.ContsLMflag = False
            setIndicator(self.pushButton_LMReadConts,'rgb(161,0,0)')

    def setDV(self,on_off):
        self.tempDV = on_off

    def connectServer(self, key, server):
        try:
            self.serversList[str(key)] = server
            self.refreshServerIndicator()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

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
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def refreshServerIndicator(self):
        try:
            optional = []#This optional will reconstruct combobox multiple time when you disconnect/connect server individually
            flag = True
            for key in self.serversList:
                if self.serversList[str(key)] == False and not str(key) in optional:
                    flag = False
                    
            if flag:
                setIndicator(self.pushButton_Servers, 'rgb(0, 170, 0)')

                for key, DevicePropertyList in self.DeviceList.items():#Reconstruct all combobox when all servers are connected
                    ReconstructComboBox(DevicePropertyList['ComboBoxServer'], DevicePropertyList['ServerNeeded'])

                self.Refreshinterface()
            else:
                setIndicator(self.pushButton_Servers, 'rgb(161, 0, 0)')
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)
        for key, DevicePropertyList in self.DeviceList.items():
            RefreshIndicator(DevicePropertyList['ServerIndicator'], DevicePropertyList['ServerObject'])
            RefreshIndicator(DevicePropertyList['DeviceIndicator'], DevicePropertyList['DeviceObject'])
    def SetupPlots(self):
        for PlotName in self.Plotlist:
            Setup1DPlot(self.Plotlist[PlotName]['PlotObject'], self.Plotlist[PlotName]['Layout'], self.Plotlist[PlotName]['Title'], self.Plotlist[PlotName]['YAxisName'], self.Plotlist[PlotName]['YUnit'], self.Plotlist[PlotName]['XAxisName'], self.Plotlist[PlotName]['XUnit'])#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        
    def moveDefault(self):
        self.move(10,170)
        
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))
