from __future__ import division
import sys
import os
import twisted
from PyQt5 import QtCore, QtGui, QtTest, uic, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
import numpy as np
import pyqtgraph as pg
#import exceptions
import time
import threading
import copy
from scipy.signal import detrend
from datetime import date
#importing a bunch of stuff


path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(path, 'TransportGateSweepSetting'))

import TransportGateSweepSetting


#CHECK w/ CARLOS ABOUT THESE
ADC_CONVERSIONTIME = 250
ADC_AVGSIZE = 1

adc_offset = np.array([0.29391179, 0.32467712])
adc_slope = np.array([1.0, 1.0])

MultiSweeperWindowUI, QtBaseClass = uic.loadUiType(os.path.join(path, "MultiSweeperWindow.ui"))
Ui_ServerList, QtBaseClass = uic.loadUiType(os.path.join(path, "requiredServers.ui"))

#Not required, but strongly recommended functions used to format numbers in a particular way.
#sys.path.append(sys.path[0]+'\Resources')
from DEMONSFormat import *

class Window(QtGui.QMainWindow, MultiSweeperWindowUI):

    def __init__(self, reactor, DEMONS, parent=None):
        super(Window, self).__init__(parent)
        from labrad.units import V, mV, us, ns, GHz, MHz, Hz, K, deg, s
        self.reactor = reactor
        self.parent = parent
        self.DEMONS = DEMONS
        self.setupUi(self)


        self.SettingWindow = TransportGateSweepSetting.Setting(self.reactor, self)
        self.pushButton_Setting.clicked.connect(lambda: openWindowServers(self.SettingWindow,self.serversList,self.AvailableDevices))
        
        self.serversList = { #Dictionary including toplevel server received from labrad connect
            'dv': False,
            'DACADC': False, 
            'SR830_0': False,
            'SR830_1': False,
            'Lakeshore': False,
            'Keithley2450': False,
            'AMI430_X': False,
            'AMI430_Y': False,
            'AMI430_Z': False,
        }

        self.AvailableDevices = {}
        self.DeviceList = {}#self.DeviceList['Device Name'][Device Property]

        # self.DeviceList['Voltage_LI_Device'] = {
        #     'DeviceObject': False,
        #     'ServerObject': False,
        #     'ComboBoxServer': self.comboBox_Voltage_LI_SelectServer,
        #     'ComboBoxDevice': self.comboBox_Voltage_LI_SelectDevice,
        #     'ServerIndicator': self.pushButton_Voltage_LI_ServerIndicator,
        #     'DeviceIndicator': self.pushButton_Voltage_LI_DeviceIndicator,
        #     'ServerNeeded': ['SR830'],
        # }
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
        # self.DeviceList['Current_LI_Device'] = {
        #     'DeviceObject': False,
        #     'ServerObject': False,
        #     'ComboBoxServer': self.comboBox_Current_LI_SelectServer,
        #     'ComboBoxDevice': self.comboBox_Current_LI_SelectDevice,
        #     'ServerIndicator': self.pushButton_Current_LI_ServerIndicator,
        #     'DeviceIndicator': self.pushButton_Current_LI_DeviceIndicator, 
        #     'ServerNeeded': ['SR830'],
        # }

        # self.DeviceList['DataAquisition_Device'] = {
        #     'DeviceObject': False,
        #     'ServerObject': False,
        #     'ComboBoxServer': self.comboBox_DataAquisition_SelectServer,
        #     'ComboBoxDevice': self.comboBox_DataAquisition_SelectDevice,
        #     'ServerIndicator': self.pushButton_DataAquisition_ServerIndicator,
        #     'DeviceIndicator': self.pushButton_DataAquisition_DeviceIndicator, 
        #     'ServerNeeded': ['DACADC'],
        # }

        self.Parameter = {
            'DeviceName': str(date.today()) + ' - Default',
            'WaitTime': 0,
            'Delta': 0,
            'BufferRamp': 0,
        } 
        self.lineEdit = {
            'DeviceName': self.lineEdit_Device_Name,
            'WaitTime': self.lineEdit_WaitTime,
            'Delta': self.lineEdit_Delta,
            'BufferRamp': self.lineEdit_BufferRamp,

        }

        self.lineEdit_Device_Name.setText(str(date.today()) + ' - Default')
        self.instrumentBus = {}
        self.indep_vars = []
        self.dep_vars = []
        self.custom_vars = []
        self.Queue = []
        self.flag = True
        self.livePlot = False
        self.currentpoints = 0

        self.DetermineEnableConditions()
        self.setupTable()

        self.SettingWindow.busset.connect(lambda: self.importBus(self.SettingWindow.bus))#print(self.SettingWindow.bus))
        self.pushButton_Query.clicked.connect(lambda: self.query())
        self.pushButton_AddQueue.clicked.connect(lambda: self.addQueue())
        self.pushButton_AddLoop.clicked.connect(lambda: self.addLoop())
        self.pushButton_ClearLoops.clicked.connect(lambda: self.clearLoops())
        self.pushButton_DeleteQueue.clicked.connect(lambda: self.deleteQueue())

        self.lineEdit_Device_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.Parameter, 'DeviceName', self.lineEdit))
        self.lineEdit_WaitTime.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'WaitTime', self.lineEdit,[0.0,5.0]))
        self.lineEdit_Delta.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'Delta', self.lineEdit,[-1.0,1.0]))
        self.lineEdit_BufferRamp.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'BufferRamp', self.lineEdit,[0,4]))

        self.pushButton_StartSweep.clicked.connect(lambda: self.StartSweep())
        self.pushButton_AbortSweep.clicked.connect(lambda: self.AbortSweep())
        
        self.checkBox_LivePlot.stateChanged.connect(lambda: self.LivePlotChanged())
        #self.SetupPlots()
        self.Refreshinterface()

    def DetermineEnableConditions(self):
        self.ButtonsCondition = {
            self.comboBox_LivePlotDep: self.livePlot,
            self.comboBox_LivePlotIndep: self.livePlot
        }

    @inlineCallbacks
    def connectServer(self, key, server):
        try:
            self.serversList[str(key)] = server
            if key != 'dv':
                yield self.refreshDeviceList(server,key)
            #self.refreshServerIndicator()
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
            #self.refreshServerIndicator()
            self.Refreshinterface()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        self.printInfo()
        RefreshButtonStatus(self.ButtonsCondition)
        ReconstructComboBox(self.comboBox_LoopVar,self.indep_vars)
        ReconstructComboBox(self.comboBox_LivePlotIndep,self.indep_vars)
        ReconstructComboBox(self.comboBox_LivePlotDep,self.dep_vars+self.custom_vars)

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

    @inlineCallbacks
    def importBus(self,bus_dictionary):

        #this moves all custom variables to the back
        for instrument in bus_dictionary:
            if bus_dictionary[instrument]['InstrumentType'] == 'CVar':
                removed_dict = bus_dictionary.pop(instrument)
                bus_dictionary[instrument] = removed_dict
        self.instrumentBus = bus_dictionary
        yield self.query()
        self.clearLoops()
        self.Refreshinterface()

    def clearLoops(self):
        self.Queue = []
        for row in range(0,self.tableWidget_Queue.rowCount()-1):
            self.tableWidget_Queue.removeRow(1)
        self.Refreshinterface()

    @inlineCallbacks
    def query(self):
        self.indep_vars = []
        self.dep_vars = []
        self.custom_vars = []
        self.reference_time = time.time()
        indep_vals = []
        dep_vals = []
        custom_vals = []

        dvfolder = self.DEMONS.MeasurementWindows['LabRAD'].lineEdit_DataVaultFolder.text()
        self.label_DVFolder.setText(dvfolder)

        indep_vals.append(time.time()-self.reference_time)
        self.indep_vars.append('timestamp')
        for instrument in self.instrumentBus:
            if 'ReadFn' in self.instrumentBus[instrument]:
                g = yield self.instrumentBus[instrument]['ReadFn'](self.instrumentBus[instrument])
                if self.instrumentBus[instrument]['InstrumentType'] == 'SR830' or self.instrumentBus[instrument]['Measurement'] == 'Input':
                    counter = 0
                    if g is not None:
                        for output_value in g:
                            dep_vals.append(output_value)
                            if self.instrumentBus[instrument]['InstrumentType'] == 'SR830':
                                if self.instrumentBus[instrument]['LIReading'] == 'X/Y':
                                    if counter == 0:
                                        self.dep_vars.append(str(instrument + '_X'))
                                    elif counter == 1:
                                        self.dep_vars.append(str(instrument + '_Y'))
                                elif self.instrumentBus[instrument]['LIReading'] == 'R/T':
                                    if counter == 0:
                                        self.dep_vars.append(str(instrument + '_R'))
                                    elif counter == 1:
                                        self.dep_vars.append(str(instrument + '_Th'))
                            else:
                                self.dep_vars.append(str(instrument + '_' + str(counter)))
                            counter += 1
                elif self.instrumentBus[instrument]['Measurement'] == 'Output':
                    counter = 0
                    if g is not None:
                        for output_value in g:
                            indep_vals.append(output_value)
                            self.indep_vars.append(str(instrument + '_' + str(counter)))
                            counter += 1
            if self.instrumentBus[instrument]['InstrumentType'] == 'CVar':
                self.custom_vars.append(self.instrumentBus[instrument]['Name'])
                custom_vals.append(self.instrumentBus[instrument]['CustomFn'](self.instrumentBus[instrument],self.dep_vars,[dep_vals])[0])
        clearLayout(self.hLayout_Query)
        for counter in range(0,len(self.indep_vars)):
            label = QtWidgets.QLabel(str(self.indep_vars[counter] + '\n' + str(indep_vals[counter])))
            label.setStyleSheet("color: rgb(168,168,168);background-color:rgb(0,0,0);border: 2px solid  rgb(131,131,131); border-radius: 5px")
            self.hLayout_Query.addWidget(label)
        for counter in range(0,len(self.dep_vars)):
            label = QtWidgets.QLabel(str(self.dep_vars[counter] + '\n' + str(dep_vals[counter])))
            label.setStyleSheet("color: rgb(168,168,168);background-color:rgb(0,0,0);border: 2px solid  rgb(131,131,131); border-radius: 5px")

            self.hLayout_Query.addWidget(label)
        for counter in range(0,len(self.custom_vars)):
            label = QtWidgets.QLabel(str(self.custom_vars[counter] + '\n' + str(custom_vals[counter])))
            label.setStyleSheet("color: rgb(168,168,168);background-color:rgb(0,0,0);border: 2px solid  rgb(131,131,131); border-radius: 5px")

            self.hLayout_Query.addWidget(label)

        return indep_vals, dep_vals, custom_vals

    @inlineCallbacks #this does what query does but without setting the widgets or updating anything
    def queryFast(self):
        indep_vals = []
        dep_vals = []
        custom_vals = []
        ti = time.time()
        indep_vals.append(ti-self.reference_time)
        #self.currentpoints += 1
        #self.progressBar_Loop.setValue(self.currentpoints)
        for instrument in self.instrumentBus:
            if 'ReadFn' in self.instrumentBus[instrument]:
                g = yield self.instrumentBus[instrument]['ReadFn'](self.instrumentBus[instrument])
                if self.instrumentBus[instrument]['InstrumentType'] == 'SR830' or self.instrumentBus[instrument]['Measurement'] == 'Input':
                    if g is not None:
                        for output_value in g:
                            dep_vals.append(output_value)
                elif self.instrumentBus[instrument]['Measurement'] == 'Output':
                    if g is not None:
                        for output_value in g:
                            indep_vals.append(output_value)
            if self.instrumentBus[instrument]['InstrumentType'] == 'CVar':
                custom_vals.append(self.instrumentBus[instrument]['CustomFn'](self.instrumentBus[instrument],self.dep_vars,[dep_vals])[0])

        return indep_vals, dep_vals, custom_vals
    
    def addQueue(self):
        try:
            dependent_var = self.comboBox_LoopVar.currentText()
            start_point = self.lineEdit_LoopStart.text()
            end_point = self.lineEdit_LoopEnd.text()
            steps = self.lineEdit_LoopSteps.text()
            steps = int(steps)
            start_point = float(start_point)
            end_point = float(end_point)
            lst = dependent_var.split('_')
            instrument_desired = lst[0]
            if instrument_desired in self.instrumentBus.keys():
                self.Queue.append([[instrument_desired,start_point,end_point,steps,dependent_var]])
                lbl, var,start,stop,ste = QtGui.QTableWidgetItem(),QtGui.QTableWidgetItem(),QtGui.QTableWidgetItem(),QtGui.QTableWidgetItem(),QtGui.QTableWidgetItem()
                lbl.setText(str(len(self.Queue)))
                var.setText(str(instrument_desired))
                start.setText(str(start_point))
                stop.setText(str(end_point))
                ste.setText(str(steps))
                array = [lbl,var,start,stop,ste]
                self.tableWidget_Queue.insertRow(self.tableWidget_Queue.rowCount())
                for i in range(0,5):
                    self.tableWidget_Queue.setItem(self.tableWidget_Queue.rowCount() - 1,i,array[i])
            print(self.Queue)
            self.formatTable(num=1)
            self.printInfo()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)



    def addLoop(self):
        try:
            if len(self.Queue) > 0:
                dependent_var = self.comboBox_LoopVar.currentText()
                start_point = self.lineEdit_LoopStart.text()
                end_point = self.lineEdit_LoopEnd.text()
                steps = self.lineEdit_LoopSteps.text()
                steps = int(steps)
                start_point = float(start_point)
                end_point = float(end_point)
                lst = dependent_var.split('_')
                instrument_desired = lst[0]
                if instrument_desired in self.instrumentBus.keys():
                    self.Queue[-1].append([instrument_desired,start_point,end_point,steps,dependent_var])
                    lbl, var,start,stop,ste = QtGui.QTableWidgetItem(),QtGui.QTableWidgetItem(),QtGui.QTableWidgetItem(),QtGui.QTableWidgetItem(),QtGui.QTableWidgetItem()
                    lbl.setText('')
                    var.setText(str(instrument_desired))
                    #var.setText(str(dependent_var))
                    start.setText(str(start_point))
                    stop.setText(str(end_point))
                    ste.setText(str(steps))
                    array = [lbl,var,start,stop,ste]
                    self.tableWidget_Queue.insertRow(self.tableWidget_Queue.rowCount())
                    for i in range(0,5):
                        self.tableWidget_Queue.setItem(self.tableWidget_Queue.rowCount() - 1,i,array[i])
            print(self.Queue)
            self.formatTable(num=1)
            self.printInfo()
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    #print current contents of self.Queue[] into the textbrowser_loops
    def printInfo(self):
        totalstring = ''
        for line in self.Queue:
            if len(line) == 1:
                totalstring += str(line[0][0]) + ': ' +  str(line[0][1])+','+str(line[0][2])+','+str(line[0][3])+'\n'
            else:
                counter = 0
                for step in line:
                    totalstring += '->'*counter + str(step[0]) + ': ' +  str(step[1])+','+str(step[2])+','+str(step[3])+'\n'
                    counter += 1
        
        #self.textBrowser_Loops.setText(totalstring)

    @inlineCallbacks
    def StartSweep(self):
        #initialize all the datavault things - create file, write parameters/comment, etc.
        self.flag = True
        datavault = self.serversList['dv']


        #also need to figure out which direction delta is in and write it down - will matter if delta != 0
        if self.Parameter['BufferRamp'] == 2:
            if 'p0' not in self.indep_vars:
                self.indep_vars.append('p0')
            if 'n0' not in self.indep_vars:
                self.indep_vars.append('n0')
        print('Queue Started')
        for Current_Loop in self.Queue:
            #[ImageNumber,ImageDir] = CreateDataVaultFile(datavault,self.Parameter['DeviceName'],self.indep_vars,self.dep_vars+self.custom_vars)
            file = yield datavault.new(self.Parameter['DeviceName'],self.indep_vars,self.dep_vars+self.custom_vars) 
            ImageNumber = file[1][0:5]
            print('Loop Started')

            saveDataToSessionFolder(self.winId(), self.sessionFolder, str(ImageNumber)+ ' - ' + self.Parameter['DeviceName'])

            print('DV ID: '+ ImageNumber)
            if self.livePlot:
                lp_x_axis = self.comboBox_LivePlotIndep.currentText()
                lp_y_axis = self.comboBox_LivePlotDep.currentText()



            for instrument in self.instrumentBus:
                for key in self.instrumentBus[instrument]:
                    not_recorded_list = ['Name','DeviceObject','Device','DACADCDevice','DACADCDeviceObject','ReadFn','WriteFn','CustomFn']
                    if (key not in not_recorded_list) and self.instrumentBus[instrument][key] is not None:
                        datavault.add_parameter(str(str(instrument)+'_'+str(key)),self.instrumentBus[instrument][key])
            self.totalpoints = 1
            for row in Current_Loop:
                self.totalpoints = self.totalpoints * (row[3]+1)
                if True or self.livePlot:
                    if True or row[0] == lp_x_axis.split('_')[0]:
                        lp_min = min([float(row[1]),float(row[2])])
                        lp_max = max([float(row[1]),float(row[2])])
                        lp_steps = int(row[3]) + 1
                datavault.add_parameter(str(row[4]) + str('Loop-Start'),row[1])
                datavault.add_parameter(str(row[4]) + str('Loop-End'),row[2])
                datavault.add_parameter(str(row[4]) + str('Loop-Steps'),row[3])
                datavault.add_parameter(str(row[4]) + '_pnts', lp_steps)
                datavault.add_parameter(str(row[4]) + '_rng',(lp_min,lp_max))
            if self.livePlot:
                #datavault.add_parameter(lp_x_axis + '_pnts', lp_steps)
                #datavault.add_parameter(lp_x_axis + '_rng', (lp_min,lp_max))
                datavault.add_parameter('live_plots', [(lp_x_axis,lp_y_axis)])

            AddParameterToDataVault(datavault, self.Parameter)

            self.progressBar_Loop.setRange(0,self.totalpoints)
            self.progressBar_Loop.setValue(0)

            self.currentpoints = 0 
            all_variables = self.indep_vars + self.dep_vars + self.custom_vars
            yield RecursiveLoop(self.instrumentBus,Current_Loop,self.queryFast,datavault,self,self.Parameter['WaitTime'],self.reactor,self.Parameter['BufferRamp'],all_variables,self.Parameter['Delta'],self.progressBar_Loop)
            datavault.add_comment(str(self.textEdit_Comment.toPlainText()))
            print('Loop Complete')
            self.progressBar_Loop.setValue(self.totalpoints)

        print('Queue Complete')


    def AbortSweep(self):
        self.flag = False
        self.progressBar_Loop.setValue(0)

    def LivePlotChanged(self):
        self.livePlot = self.checkBox_LivePlot.isChecked()
        self.Refreshinterface()

    def setupTable(self):
        self.tableWidget_Queue.horizontalHeader().hide()
        self.tableWidget_Queue.verticalHeader().hide()

        self.tableWidget_Queue.cellDoubleClicked.connect(self.editQueuef)
        self.tableWidget_Queue.cellChanged.connect(self.editQueue)

        self.tableWidget_Queue.setColumnCount(5)
        self.tableWidget_Queue.insertRow(0)
        headers = []
        for i in range(0,5):
            headers.append(QtGui.QTableWidgetItem())

        headers[0].setText('Queue Step')
        headers[0].setForeground(QBrush(QColor(131,131,131)))
        headers[1].setText('Variable')
        headers[1].setForeground(QBrush(QColor(131,131,131)))
        headers[2].setText('Start')
        headers[2].setForeground(QBrush(QColor(131,131,131)))
        headers[3].setText('Stop')
        headers[3].setForeground(QBrush(QColor(131,131,131)))
        headers[4].setText('Steps')
        headers[4].setForeground(QBrush(QColor(131,131,131)))
        for i in range(0,5):
            self.tableWidget_Queue.setItem(0,i,headers[i])
            self.tableWidget_Queue.item(0, i).setFont(QtGui.QFont("MS Shell Dlg 2",weight=QtGui.QFont.Bold))
            self.tableWidget_Queue.item(0, i).setFlags(QtCore.Qt.NoItemFlags)

    # clears the double - clicked on cell of the table so it can be replaced
    def editQueuef(self,r,c): 
        try:
            if self.tableWidget_Queue.item(r,0) != '':
                item = self.tableWidget_Queue.item(r,c)
                item.setText('')
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    #edit a single cell of the table and update the queue accordingly
    def editQueue(self,r,c): 
        try:
            if r > 0 and self.tableWidget_Queue.item(r,0).text() != '':
                text = self.tableWidget_Queue.item(r,c).text()
                val = ''
                if text != '' and c == 1:
                    val = str(text)
                elif text != '' and (c == 2 or c == 3):
                    val = float(text)
                elif text != '' and c == 4:
                    val = int(text)
                if val != '' and val != self.Queue[int(self.tableWidget_Queue.item(r,0).text())-1][0][c-1]:
                    self.Queue[int(self.tableWidget_Queue.item(r,0).text())-1][0][c-1] = val
                    print('Updated queue:')
                    print(self.Queue)
            if r > 0 and self.tableWidget_Queue.item(r,0).text() == '':
                count = 0
                rowloop = r
                while self.tableWidget_Queue.item(rowloop,0).text() == '':
                    rowloop -= 1
                    count += 1
                queue_step = int(self.tableWidget_Queue.item(rowloop,0).text()) - 1
                text = self.tableWidget_Queue.item(r,c).text()
                val = ''
                if text != '' and c == 1:
                    val = str(text)
                elif text != '' and (c == 2 or c == 3):
                    val = float(text)
                elif text != '' and c == 4:
                    val = int(text)
                if val != '' and val != self.Queue[queue_step][count][c-1]:
                    self.Queue[queue_step][count][c-1] = val
                    print('Updated queue:')
                    print(self.Queue)


        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

 


    def deleteQueue(self):
        r = self.tableWidget_Queue.currentRow()
        totalrows = self.tableWidget_Queue.rowCount()
        print(r)
        if r > -1:
            if self.tableWidget_Queue.item(r,0).text() != '': 
                if r + 1 == totalrows or self.tableWidget_Queue.item(r+1, 0).text() != '':
                    #case where we want to delete a first step and there's no second step
                    self.Queue.pop(int(self.tableWidget_Queue.item(r,0).text())-1)
                    self.tableWidget_Queue.removeRow(r)
                    counter = r
                    while counter < totalrows - 1:
                        step = self.tableWidget_Queue.item(counter,0).text()
                        if step != '':
                            self.tableWidget_Queue.item(counter,0).setText(str(int(step)-1))
                        counter += 1
                    print('Updated queue:')
                    print(self.Queue)
                else:
                    #case where we want to delete a first step and there is a second step
                    current_step = int(self.tableWidget_Queue.item(r,0).text())
                    self.Queue[current_step-1].pop(0)
                    self.tableWidget_Queue.removeRow(r)
                    print('test')
                    print(r)
                    print(current_step)
                    self.tableWidget_Queue.item(r,0).setText(str(current_step))
                    # counter = r + 1
                    # while counter < totalrows - 1:
                    #     step = self.tableWidget_Queue.item(counter,0).text()
                    #     if step != '':
                    #         self.tableWidget_Queue.item(counter,0).setText(str(int(step)-1))
                    #     counter += 1
                    print('Updated queue:')
                    print(self.Queue)
            elif self.tableWidget_Queue.item(r,0).text() == '':
                count = 0
                rowloop = r
                while self.tableWidget_Queue.item(rowloop,0).text() == '':
                    rowloop -= 1
                    count += 1
                queue_step = int(self.tableWidget_Queue.item(rowloop,0).text()) - 1
                self.Queue[queue_step].pop(count)
                self.tableWidget_Queue.removeRow(r)
                print('Updated queue:')
                print(self.Queue)


    def formatTable(self,num=None):
        if num == 1:
            for c in range(0, 5):
                for r in range(0, self.tableWidget_Queue.rowCount()):
                    if self.tableWidget_Queue.item(r, c) != None:
                        self.tableWidget_Queue.item(r, c).setBackground(QtGui.QColor(0,0,0))
                        self.tableWidget_Queue.item(r, c).setForeground(QBrush(QColor(131,131,131)))
                        if c not in [2,3,4]:
                            self.tableWidget_Queue.item(r, c).setFlags(QtCore.Qt.NoItemFlags)
                            #self.tableWidget_Queue.item(r,c).setBackground(QBrush(QColor(100,100,150)))

                        else:
                            
                            item = self.tableWidget_Queue.item(r, c)
                            #if item.text() == '':
                            #    item.setText(self.backtext1)
                            #item.setForeground(QBrush(QColor(0,0,0)))
        else:
            pass



class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))
