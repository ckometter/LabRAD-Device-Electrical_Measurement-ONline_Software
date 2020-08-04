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
sys.path.append(os.path.join(path, 'TransportGateSweepSetting'))

import TransportGateSweepSetting


#CHECK w/ CARLOS ABOUT THESE
ADC_CONVERSIONTIME = 250
ADC_AVGSIZE = 1

adc_offset = np.array([0.29391179, 0.32467712])
adc_slope = np.array([1.0, 1.0])

TransportGateSweepWindowUI, QtBaseClass = uic.loadUiType(os.path.join(path, "TransportGateSweepWindow.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

#Not required, but strongly recommended functions used to format numbers in a particular way.
#sys.path.append(sys.path[0]+'\Resources')
from DEMONSFormat import *

class Window(QtGui.QMainWindow, TransportGateSweepWindowUI):

    def __init__(self, reactor, DEMONS, parent=None):
        super(Window, self).__init__(parent)
        from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg, s
        self.reactor = reactor
        self.parent = parent
        self.DEMONS = DEMONS
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.SettingWindow = TransportGateSweepSetting.Setting(self.reactor, self)
        self.pushButton_Setting.clicked.connect(lambda: openWindowServers(self.SettingWindow,self.serversList,self.AvailableDevices))

        self.serversList = { #Dictionary including toplevel server received from labrad connect
            'dv': False,
            'DACADC': False, 
            'SR830': False,
            'Lakeshore': False,
        }
        self.AvailableDevices = {}
        self.DeviceList = {}#self.DeviceList['Device Name'][Device Property]

        self.DeviceList['Voltage_LI_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Voltage_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_Voltage_LI_SelectDevice,
            'ServerIndicator': self.pushButton_Voltage_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_Voltage_LI_DeviceIndicator,
            'ServerNeeded': ['SR830'],
        }
        self.units = {
            'Hz': Hz,
            'V': V,
            'mV': mV,
            'us': us,
            'ns': ns,
            'GHz': GHz,
            'MHz': MHz,
            's': s
            
        }
        self.DeviceList['Current_LI_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Current_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_Current_LI_SelectDevice,
            'ServerIndicator': self.pushButton_Current_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_Current_LI_DeviceIndicator, 
            'ServerNeeded': ['SR830'],
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
            'LI_Excitation': 0.0,
            'LI_Timeconstant': 0.1,
            'LI_Frequency': 17.777,
            'V_LI_Sensitivity': 0,
            'I_LI_Sensitivity': 0,
            'Voltage_LI_Gain': 1.0,
            'Current_LI_Gain': 1.0,
            'Gates': 1,
            'n0_Start': -1.0,
            'n0_End': 1.0,
            'n0_Steps':10,
            'p0_Start': 0.0,
            'p0_End': 0.0,
            'p0_Steps':1,
            'Delta': 0.0,
            'FourTerminal_Delay': 0.3,
            'VbChannel': 0,
            'VtChannel': 1,
            'Setting_RampDelay': 0.0001,
            'Setting_RampStepSize': 0.01,
            'Setting_WaitTime': 2.0,
            'Bias_Resistor' : 0.0,
            'Current_Resistor': 0.0
        } 

        self.lineEdit = {
            'DeviceName': self.lineEdit_Device_Name,
            'LI_Excitation': self.lineEdit_LI_Excitation,
            'LI_Timeconstant': self.lineEdit_LI_Timeconstant,
            'LI_Frequency': self.lineEdit_LI_Frequency,
            'V_LI_Sensitivity': self.lineEdit_V_LI_Sensitivity,
            'I_LI_Sensitivity': self.lineEdit_I_LI_Sensitivity,
            'n0_Start': self.lineEdit_n0_Start,
            'n0_End': self.lineEdit_n0_End,
            'n0_Steps': self.lineEdit_n0_Steps,
            'p0_Start': self.lineEdit_p0_Start,
            'p0_End': self.lineEdit_p0_End,
            'p0_Steps': self.lineEdit_p0_Steps,
            'Gates': self.comboBox_Gates,
            'Delta': self.lineEdit_Delta,
            'FourTerminal_Delay': self.lineEdit_FourTerminal_Delay,
            'VbChannel': self.lineEdit_DataAquisition_VbChannel,
            'VtChannel': self.lineEdit_DataAquisition_VtChannel,
            'Bias_Resistor' : self.lineEdit_BiasResistor,
            'Current_Resistor': self.lineEdit_CurrentResistor

        }

        #for key in self.lineEdit:
        #    if not isinstance(self.Parameter[key], str):
        #        UpdateLineEdit_Bound(self.Parameter, key, self.lineEdit)


        self.Plotlist = {}
        # self.Plotlist['VoltagePlot'] = {
        #     'PlotObject': pg.PlotWidget(parent = None),
        #     'PlotData': [[], []],
        #     'Layout': self.Layout_FourTerminalPlot1,
        #     'Title': 'Voltage',
        #     'XAxisName': 'Gate Voltage',
        #     'XUnit':"V",
        #     'YAxisName': 'Voltage',
        #     'YUnit': "V",
        # }

        # self.Plotlist['CurrentPlot'] = {
        #     'PlotObject': pg.PlotWidget(parent = None),
        #     'PlotData': [[], []],
        #     'Layout': self.Layout_FourTerminalPlot2,
        #     'Title': 'Current',
        #     'XAxisName': 'Gate Voltage',
        #     'XUnit':"V",
        #     'YAxisName': 'Current',
        #     'YUnit': "A",
        # }

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

        self.SettingWindow.busset.connect(lambda: print(self.SettingWindow.bus))
        self.lineEdit_Device_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.Parameter, 'DeviceName', self.lineEdit))

        self.lineEdit_LI_Excitation.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Excitation', self.lineEdit,[0.0,5.0]))
        self.pushButton_LI_Excitation_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation'],'V'))
        self.pushButton_LI_Excitation_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation'],self.units['V']))#Send to Voltage Lock in
        self.lineEdit_LI_Timeconstant.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Timeconstant', self.lineEdit))
        self.pushButton_LI_Timeconstant_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant'],'s'))
        self.pushButton_LI_Timeconstant_Incr.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant_up, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant'],self.units['s']))#Send to Voltage Lock in
        self.pushButton_LI_Timeconstant_Decr.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant_down, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant'],self.units['s']))#Send to Voltage Lock in
        #if (self.DeviceList['Current_LI_Device']['DeviceObject'] != False):
        #    self.pushButton_LI_Timeconstant_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant']))#Send to Current Lock in
        self.lineEdit_LI_Frequency.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Frequency', self.lineEdit))
        self.pushButton_LI_Frequency_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'], 'Hz'))
        self.pushButton_LI_Frequency_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'],self.units['Hz']))#Send to Voltage Lock in
        self.lineEdit_V_LI_Sensitivity.editingFinished.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sensitivity,self.Parameter,'V_LI_Sensitivity',self.lineEdit['V_LI_Sensitivity'],'V'))
        self.pushButton_V_LI_Sensitivity_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sensitivity,self.Parameter,'V_LI_Sensitivity', self.lineEdit['V_LI_Sensitivity'],'V'))
        self.pushButton_V_LI_Sensitivity_Incr.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sensitivity_up,self.Parameter,'V_LI_Sensitivity', self.lineEdit['V_LI_Sensitivity'],self.units['V']))
        self.pushButton_V_LI_Sensitivity_Decr.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sensitivity_down,self.Parameter,'V_LI_Sensitivity', self.lineEdit['V_LI_Sensitivity'],self.units['V']))

        self.lineEdit_I_LI_Sensitivity.editingFinished.connect(lambda: ReadEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sensitivity,self.Parameter,'I_LI_Sensitivity',self.lineEdit['I_LI_Sensitivity'],'V'))
        self.pushButton_I_LI_Sensitivity_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sensitivity,self.Parameter,'I_LI_Sensitivity', self.lineEdit['I_LI_Sensitivity'],'V'))
        self.pushButton_I_LI_Sensitivity_Incr.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sensitivity_up,self.Parameter,'I_LI_Sensitivity', self.lineEdit['I_LI_Sensitivity'],self.units['V']))
        self.pushButton_I_LI_Sensitivity_Decr.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sensitivity_down,self.Parameter,'I_LI_Sensitivity', self.lineEdit['I_LI_Sensitivity'],self.units['V']))

        self.lineEdit_BiasResistor.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter,'Bias_Resistor',self.lineEdit))
        self.lineEdit_CurrentResistor.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter,'Current_Resistor',self.lineEdit))

        self.comboBox_Voltage_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Voltage_LI_Device', self.serversList, str(self.DeviceList['Voltage_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Voltage_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Voltage_LI_Device', str(self.DeviceList['Voltage_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        
        self.comboBox_Current_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Current_LI_Device', self.serversList, str(self.DeviceList['Current_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Current_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Current_LI_Device', str(self.DeviceList['Current_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))

        self.comboBox_DataAquisition_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'DataAquisition_Device', self.serversList, str(self.DeviceList['DataAquisition_Device']['ComboBoxServer'].currentText())))
        self.comboBox_DataAquisition_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'DataAquisition_Device', str(self.DeviceList['DataAquisition_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_DataAquisition_VbChannel.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'VbChannel', self.lineEdit, None, int))
        self.lineEdit_DataAquisition_VtChannel.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'VtChannel', self.lineEdit, None, int))

        self.comboBox_Gates.currentIndexChanged.connect(lambda: UpdateComboBox(self.Parameter, 'Gates',self.lineEdit))
        self.lineEdit_n0_Start.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'n0_Start', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_n0_End.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'n0_End', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_n0_Steps.editingFinished.connect(lambda: UpdateLineEdit_Int(self.Parameter, 'n0_Steps', self.lineEdit))
        self.lineEdit_p0_Start.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'p0_Start', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_p0_End.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'p0_End', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_p0_Steps.editingFinished.connect(lambda: UpdateLineEdit_Int(self.Parameter, 'p0_Steps', self.lineEdit))
        self.lineEdit_Delta.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter,'Delta', self.lineEdit,[-1.0, 1.0]))

        self.lineEdit_FourTerminal_Delay.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_Delay', self.lineEdit))
        #self.pushButton_FourTerminal_NoSmTpTSwitch.clicked.connect(lambda: Toggle_NumberOfSteps_StepSize(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.label_FourTerminalNumberofstep, 'Volt per Step', self.lineEdit))  

        self.pushButton_StartFourTerminalSweep.clicked.connect(self.StartMeasurement)
        self.pushButton_AbortFourTerminalSweep.clicked.connect(lambda: self.DEMONS.SetScanningFlag(False))

        self.SetupPlots()
        self.Refreshinterface()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.lineEdit_Device_Name: True,
            self.pushButton_StartFourTerminalSweep: (self.DeviceList['DataAquisition_Device']['DeviceObject'] != False) and (self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False) and self.DEMONS.Scanning_Flag == False,
            self.pushButton_AbortFourTerminalSweep: self.DEMONS.Scanning_Flag == True,
            self.comboBox_DataAquisition_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_DataAquisition_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_DataAquisition_VbChannel: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_n0_Start: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_n0_End: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_n0_Steps: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_p0_Start: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_p0_End: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_p0_Steps: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_Delay: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Timeconstant: self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Timeconstant_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Timeconstant_Incr: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Timeconstant_Decr: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Frequency: self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Frequency_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False  and self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Frequency_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.comboBox_Voltage_LI_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Voltage_LI_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Excitation: self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Excitation_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Excitation_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.comboBox_Current_LI_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Current_LI_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.pushButton_I_LI_Sensitivity_Incr: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_I_LI_Sensitivity_Decr: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_I_LI_Sensitivity_Read: self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_V_LI_Sensitivity_Incr: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_V_LI_Sensitivity_Decr: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_V_LI_Sensitivity_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,

        }

    @inlineCallbacks
    def StartMeasurement(self, c):
        try:
            self.DEMONS.SetScanningFlag(True)#Set scanning flag to be True, this is a flag in DEMON main Window and it is used for preventing to start multiple measurements
    
            self.Refreshinterface()#Based on flag, disable buttons
            
            lockin_number = 1
            gates = self.Parameter['Gates']
            if (self.DeviceList['Current_LI_Device']['DeviceObject'] != False):
                lockin_number = 2

            #At the beginning of the measurement, set the parameters to the lock-in
            #SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant'])
            #SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'])
            #SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation'])
            #SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sensitivity, self.Parameter,'V_LI_Sensitivity',self.lineEdit['V_LI_Sensitivity'])

            #if lockin_number == 2:
                #SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant'])
                #SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'])

            Multiplier = [self.Parameter['Voltage_LI_Gain'], self.Parameter['Current_LI_Gain']] #Voltage, Current for multiply the data
    
            ImageNumber, ImageDir = yield CreateDataVaultFile(self.serversList['dv'], 'DEMONS_Transport ' + str(self.Parameter['DeviceName']), ("i","j",'gate1','gate2'), ('Ix','Iy','Vx','Vy','p0','n0','R','sigma','t')) #Create datavault with independent variables and dependent variables, this return the datavault number and the directory
            self.lineEdit_ImageNumber.setText(ImageNumber) #set text on lineedit in GUI
            self.lineEdit_ImageDir.setText(ImageDir) #set text on lineedit in GUI
    
            yield AddParameterToDataVault(self.serversList['dv'], self.Parameter) #Add parameters to data vault
            ClearPlots(self.Plotlist) #Clear plots

            gate_ch1 = self.Parameter['VbChannel']
            gate_ch2 = self.Parameter['VtChannel']
            #sets maximum voltages gates can be ramped to
            X_MIN = -10
            X_MAX = 10
            Y_MIN = -10 
            Y_MAX = 10

            t0 = time.time()
            pxsize = (self.Parameter['n0_Steps'],self.Parameter['p0_Steps'])
            extent = (self.Parameter['n0_Start'],self.Parameter['n0_End'],self.Parameter['p0_Start'],self.Parameter['p0_End'])
            num_x = pxsize[0]
            num_y = pxsize[1]

            DELAY_MEAS = 3.0 * self.Parameter['LI_Timeconstant']*1e6
            SWEEP_MULT = 30.0
            est_time = (pxsize[0]*pxsize[1] + pxsize[1])*DELAY_MEAS*1e-6/60.0
            dt = pxsize[0]*DELAY_MEAS*1e-6/60.0
            #should probably output this in a better way
            print("Will take a total of {} mins. With each line trace taking {} ".format(float('%.4g' % est_time),float('%.4g' %  dt)))
            m, mdn = mesh(0.0, offset = (0,0), drange= (extent[2],extent[3]), nrange= (extent[0],extent[1]),gates = gates,pxsize = pxsize, delta= self.Parameter['Delta'])


            if gates == 1:
                dac_ch = [gate_ch1]
            elif gates == 2:
                dac_ch = [gate_ch1,gate_ch2]
            if lockin_number == 1:
                adc_ch = [0,1] #should probably not hardcode this in?
            if lockin_number == 2:
                adc_ch = [0,1,2,3]

            for i in range(num_y):
                Ix = np.zeros(num_x)
                Iy = np.zeros(num_x)
                Vx = np.zeros(num_x)
                Vy = np.zeros(num_x)

                vec_x = m[i,:][:,0]
                vec_y = m[i,:][:,1]
                md = mdn[i,:][:,0]
                mn = mdn[i,:][:,1]
                print(md)
                print(mn)
                mask = np.logical_and(np.logical_and(vec_x <= X_MAX, vec_x >= X_MIN),
                    np.logical_and(vec_y <= Y_MAX, vec_y >= Y_MIN))
                if np.any(mask == True):
                    start,stop = np.where(mask == True)[0][0],np.where(mask==True)[0][-1]
                    Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'],dac_ch[0],0,vec_x[start],self.Parameter['Setting_RampStepSize'],self.Parameter['Setting_RampDelay'])
                    if gates==1:
                        vstart = [vec_x[start]]
                        vstop = [vec_x[stop]]
                    if gates==2:
                        Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'],dac_ch[1],0,vec_y[start],self.Parameter['Setting_RampStepSize'],self.Parameter['Setting_RampDelay'])
                        vstart = [vec_x[start], vec_y[start]]
                        vstop = [vec_x[stop], vec_y[stop]]
                    yield SleepAsync(self.reactor, self.Parameter['LI_Timeconstant']*10.0)
                    num_points = stop - start + 1
                    print('ramp start')
                    d_tmp = yield Buffer_Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'],dac_ch, adc_ch,vstart,vstop,int(num_points*SWEEP_MULT),DELAY_MEAS/SWEEP_MULT,mult = SWEEP_MULT)
                    print('ramp end')
                    #dc.buffer_Ramp(dac_ch, adc_ch,vstart,vstop,int(num_points*SWEEP_MULT),DELAY_MEAS/SWEEP_MULT,ADC_AVGSIZE)
                    #d_read = dc.serial_poll.future(len(adc_ch), int(num_points*SWEEP_MULT))
                    #d_tmp = d_read.result()

                    #d_tmp = reshape_data(d_temp,SWEEP_MULT)

                    if lockin_number == 1:
                        bias_resistor = self.Parameter['Bias_Resistor']
                        sens1 = self.Parameter['V_LI_Sensitivity']
                        Vx[start:stop + 1],Vy[start:stop + 1] = d_tmp
                        Vx = Vx*sens1/10.0
                        Vy = Vy*sens1/10.0
                        Ix = 0.0*Ix + self.Parameter['LI_Excitation']/bias_resistor
                    elif lockin_number == 2:
                        current_resistor = self.Parameter['Current_Resistor']
                        sens1 = self.Parameter['V_LI_Sensitivity']
                        sens2 = self.Parameter['I_LI_Sensitivity']
                        Vx[start:stop + 1], Vy[start:stop+1], Ix[start:stop+1], Iy[start:stop+1] = d_tmp
                        Ix = Ix*sens2/10/current_resistor
                        Iy = Iy*sens2/10/current_resistor
                        Vx = Vx*sens1/10
                        Vy = Vy*sens1/10
                R = Vx/Ix
                sig = Ix/Vx
                j = np.linspace(0,num_x - 1,num_x)
                ii = np.ones(num_x) * i
                t1 = np.ones(num_x) * time.time() - t0
                totdata = np.array([j,ii,vec_x,vec_y,Ix,Iy,Vx,Vy,md,mn,R,sig,t1])
                self.serversLit['dv'].add(totdata)
                Plot1DData(mn, R, self.Plotlist['ResistancePlot']['PlotObject'])
                Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'],dac_ch[0],vec_x[stop],0,self.Parameter['Setting_RampStepSize'],self.Parameter['Setting_RampDelay'])
                if gates == 2:
                    Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'],dac_ch[1],vec_y[stop],0,self.Parameter['Setting_RampStepSize'],self.Parameter['Setting_RampDelay'])
                    #now, insert analyze the output to get to directly measured Ix/Iy/Vx/Vy/R, plot R v n0,write a line to DV
            FinishSweep(self,vstop)
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    @inlineCallbacks
    def FinishSweep(self, currentvoltage):
        try:
            yield SleepAsync(self.reactor, self.Parameter['Setting_WaitTime'])
            #yield Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'], self.Parameter['VbChannel'],currentvoltage[0],0.0,.05, 1000)
            if len(currentvoltage) == 2:
                yield Ramp_DACADC(self.DeviceList['DataAquisition_Device']['DeviceObject'], self.Parameter['VtChannel'],currentvoltage[1],0.0,.05, 1000)
            self.serversList['dv'].add_comment(str(self.textEdit_Comment.toPlainText()))
            self.DEMONS.SetScanningFlag(False)
            self.Refreshinterface()
            saveDataToSessionFolder(self.winId(), self.sessionFolder, str(self.lineEdit_ImageDir.text()).replace('\\','_') + '_' + str(self.lineEdit_ImageNumber.text())+ ' - ' + 'Probe Station Screening ' + self.Parameter['DeviceName'])

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    @inlineCallbacks
    def connectServer(self, key, server):
        try:
            self.serversList[str(key)] = server
            if key != 'dv':
                yield self.refreshDeviceList(server,key)
            self.refreshServerIndicator()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    @inlineCallbacks
    def refreshDeviceList(self,server,key):
        devicenames = yield QueryDeviceList(server)
        self.AvailableDevices[key] = devicenames
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
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def refreshServerIndicator(self):
        try:
            optional = []#This optional will reconstruct combobox multiple time when you disconnect/connect server individually
            flag = True
            for key in self.serversList:
                if self.serversList[str(key)] == False and not key in optional:
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

        #if self.DeviceList['Current_LI_Device']['DeviceObject'] != False:
            #SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation'])
            #SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter,  'LI_Timeconstant', self.lineEdit['LI_Timeconstant'])
            #SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'])

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
