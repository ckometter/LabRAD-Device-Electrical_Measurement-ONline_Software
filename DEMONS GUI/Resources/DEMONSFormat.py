import numpy as np
from itertools import product
import sys
import twisted
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
import pyqtgraph as pg
#import exceptions
import time
import csv
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore, QtGui
from scipy.interpolate import griddata
import subprocess
from datetime import datetime, date

'''
Open Window function that receive the window object and open it
'''
def openWindow(window): 
    window.show()
    window.moveDefault()
    window.raise_()


#---------------------------------------------------------------------------------------------------------#         
""" The following section describes how to read and write values to various lineEdits on the GUI."""

'''
Read a funnction and update a lineEdit, use device's function and take the return value and feed it to parameter and lineEdit
'''
@inlineCallbacks
def ReadEdit_Parameter(Function, Parameter, parametername, lineEdit,unit):
    try:
        value = yield Function()
        Parameter[parametername] = value[unit]
        lineEdit.setText(formatNum(Parameter[parametername], 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)


'''
Set a funnction and update a lineEdit
'''
@inlineCallbacks
def SetEdit_Parameter(Function, Parameter, parametername, lineEdit,unit):
    try:
        dummyval = readNum(str(lineEdit.text()), None , False)
        value = yield Function(dummyval*unit)
        Parameter[parametername] = value[unit]
        lineEdit.setText(formatNum(Parameter[parametername], 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
'''
Update parameter, normally just text
Input: dictionary of parameters, key for the value to be changed, the lineEdit where the input comes from
Output: Change the parameter
'''
def UpdateLineEdit_String(parameterdict, key, lineEdit):
    parameterdict[key] = str(lineEdit[key].text())

def UpdateLineEdit_Int(parameterdict, key, lineEdit):
    parameterdict[key] = int(lineEdit[key].text())



'''
Update parameter with a bound
Input: dictionary of parameters, key for the value to be changed, the lineEdit where the input comes from, bound [lower, upper], datatype
Output: Change the parameter based on the validity of input value
'''
def UpdateLineEdit_Bound(dict, key, lineEdit, bound = None, datatype = float):
    dummystr=str(lineEdit[key].text())   #read the text
    dummyval=readNum(dummystr, None , False)
    if isinstance(dummyval, float):
        if bound == None:
            dict[key] = datatype(dummyval)
        elif (dummyval >= bound[0] and dummyval <= bound[1]):
            dict[key] = datatype(dummyval)
                
    lineEdit[key].setText(formatNum(dict[key], 6))


'''
Update parameter from a combobox rather than lineedit
'''
def UpdateComboBox(parameterDict,key,outputParams):
	dummyval = int(str(outputParams[key].currentText()))
	parameterDict[key] = dummyval

'''
Update Number of Step value, it is special because it need to switch between stepsize and number of step
Input: dictionary of parameters, key for the value to be changed, key for end, key for start, statuskey for status, the lineEdit where the input comes from, bound [lower, upper], datatype
Output: Change the parameter based on the validity of input value
'''
def UpdateLineEdit_NumberOfStep(dict, key, endkey, startkey, statuskey, lineEdit, bound = None, datatype = float):
    dummystr=str(lineEdit[key].text())   #read the text
    dummyval=readNum(dummystr, None , False)
    if isinstance(dummyval, datatype):
        if dict[statuskey] == "Numberofsteps":   #based on status, dummyval is deterimined and update the Numberof steps parameters
            dict[key] = int(round(dummyval)) #round here is necessary, without round it cannot do 1001 steps back and force
        elif dict[statuskey] == "StepSize":
            dict[key] = int(StepSizeToNumberOfSteps(dict[endkey], dict[startkey], float(dummyval)))
    if dict[statuskey] == "Numberofsteps":
        lineEdit[key].setText(formatNum(dict[key], 6))
    elif dict[statuskey] == "StepSize":
        lineEdit[key].setText(formatNum(NumberOfStepsToStepSize(dict[endkey], dict[startkey], float(dict[key])),6))

'''
Toggle between Number of Step and Step Size
Input: dictionary of parameters, key for the value to be changed, key for max, key for min, statuskey for status, label, the correct label unit like 'tesla per step', the lineEdit where the input comes from
Output: Change the parameter based on the validity of input value
'''
def Toggle_NumberOfSteps_StepSize(dict, key, endkey, startkey, statuskey, label, labelunit, lineEdit):
    if dict[statuskey] == "Numberofsteps":
        label.setText(labelunit)
        dict[statuskey] = "StepSize"
        lineEdit[key].setText(formatNum(NumberOfStepsToStepSize(dict[endkey], dict[startkey], float(dict[key])),6))
        UpdateLineEdit_NumberOfStep(dict, key, endkey, startkey, statuskey, lineEdit)
    else:
        label.setText('Number of Steps')
        dict[statuskey] = "Numberofsteps"
        lineEdit[key].setText(formatNum(dict[key],6))
        UpdateLineEdit_NumberOfStep(dict, key, endkey, startkey, statuskey, lineEdit)

'''
Simple StepSize to Number of Step Converters
'''
def StepSizeToNumberOfSteps(End, Start, SS):  #Conver stepsize to number of steps
    Numberofsteps=int(round(abs(End - Start)/float(SS))+1)
    if Numberofsteps == 1:
        Numberofsteps = 2
    return Numberofsteps

def NumberOfStepsToStepSize(Start, End, NoS):
    StepSize=float(abs(Start - End)/float(NoS - 1.0))
    return StepSize

'''
Takes in the Serverlist, based on the name(str) of deviceserver and servername, connect it.
'''
def SelectServer(DeviceList, DeviceName, Serverlist, ServerName,default_item = None):
    try:
        if str(ServerName) != '':#Avoid Select Server when combobox is reconstructed
            DeviceList[str(DeviceName)]['ServerObject'] = Serverlist[str(ServerName)]
            RedefineComboBox(DeviceList[str(DeviceName)]['ComboBoxDevice'], DeviceList[str(DeviceName)]['ServerObject'],default = default_item)
            RefreshIndicator(DeviceList[str(DeviceName)]['ServerIndicator'], DeviceList[str(DeviceName)]['ServerObject'])
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
Takes devicelist, device name(str), target which is the name of the device in list_devices() and the indicator pushbutton
Then save the selected device object to devicelist.
'''
@inlineCallbacks
def SelectDevice(DeviceList, DeviceName, target, SequentialFunction = None):
    try:
        if str(target) != 'Offline' and DeviceList[str(DeviceName)]['ServerObject'] != False and str(target) != '':#target can be blank when reconstruct the combobox
            try:
                DeviceList[str(DeviceName)]['DeviceObject'] = DeviceList[str(DeviceName)]['ServerObject']
                yield DeviceList[str(DeviceName)]['DeviceObject'].select_device(str(target))
            except Exception as inst:
                print('Connection to ' + device +  ' failed: ', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
                DeviceList[str(DeviceName)]['DeviceObject'] = False
        else:
            DeviceList[str(DeviceName)]['DeviceObject'] = False
        RefreshIndicator(DeviceList[str(DeviceName)]['DeviceIndicator'], DeviceList[str(DeviceName)]['DeviceObject'])
        if not SequentialFunction is None:
            SequentialFunction()
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
Refresh Indicator based on the connection status of device
'''
def RefreshIndicator(indicator, device):
    if device != False:
        setIndicator(indicator, 'rgb(0, 170, 0)')
    else:
        setIndicator(indicator, 'rgb(161, 0, 0)')

'''
change stylesheet of a pushbutton to certain color
'''
def setIndicator(indicator, color):
    indicator.setStyleSheet('#' + indicator.objectName() + '{background:' + color + ';border-radius: 4px;}')


'''
From server, query the list of device, post that on combobox and select the device to be offline.
It is useful for refreshing the list.
'''
@inlineCallbacks
def RedefineComboBox(combobox, server, reconnect = True,default=None):
    try:
        if server != False:
            itemlist = yield QueryDeviceList(server)
        else:
            itemlist = []
        itemlist = ['Offline'] + itemlist
        if default == None:
            if len(itemlist) != 1:
                defaultdevice = itemlist[1]
                defaultindex = 1
            else:
                defaultdevice = 'Offline'
                defaultindex = 0
        elif default != None:
            if default in itemlist:
                defaultindex = itemlist.index(default)
            else:
                defaultindex = 0
        ReconstructComboBox(combobox, itemlist)
        if reconnect:
            combobox.setCurrentIndex(defaultindex)#This part change the index which should be connect to select device.
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
given a list of item names and populate that into combobox
'''
def ReconstructComboBox(combobox, lst):
    text = combobox.currentIndex()
    combobox.clear()
    for name in lst:
        combobox.addItem(name)
    try:
        if len(lst) == 1:
            combobox.setCurrentIndex(1)
        else: 
            combobox.setCurrentIndex(text)
    except:
        combobox.setCurrentIndex(1)
'''
Based on the buttons Condition which are a dictionary with format button: Boolean and enable/disable the button based on the boolean value
'''
def RefreshButtonStatus(ButtonsCondition):
    for button in ButtonsCondition:
        button.setEnabled(ButtonsCondition[button])

'''
takes in server object and return a list of selectable device.
'''
@inlineCallbacks
def QueryDeviceList(server):
    devicelist = yield server.list_devices()
    namelist = []
    for combo in devicelist:
        namelist.append(combo[1])
    returnValue(namelist) 

'''
return True or False based on whether the pushbutton is green or red
'''
def JudgeIndicator(indicator): #based on stylesheet of indicator, return True or False
    color = 'rgb(0, 170, 0)'
    green = '#' + indicator.objectName() + '{background:' + color + ';border-radius: 4px;}'
    stylesheet = indicator.styleSheet()
    if stylesheet == green:
        return True
    else:
        return False

'''
Takes in parameter dictionary, key(str) of parameter, lineEdit that is related, device object for sending command, functionlist(list that guide to the correct function)
'''
@inlineCallbacks
def UpdateSetlineEdit(dict, key, lineEdit, device, function, bound = None, datatype = float):
    dummystr=str(lineEdit[key].text())   #read the text
    dummyval=readNum(dummystr, None , False)
    if isinstance(dummyval, float):
        if bound == None:
            dummyval = datatype(dummyval)
        elif (dummyval >= bound[0] and dummyval <= bound[1]):
            dummyval = datatype(dummyval)
    if device != False:
        try: 
            if function[0] == 'SR860':
                if function[1] == 'sensitivity':
                    yield device.sensitivity(dummyval)
                elif function[1] == 'timeconstant':
                    yield device.time_constant(dummyval)
                elif function[1] == 'frequency':
                    yield device.frequency(dummyval)
            flag = True
        except:
            flag = False
        if flag:
            dict[key] = dummyval
    else:
        dict[key] = dummyval
    lineEdit[key].setText(formatNum(dict[key], 6))

'''
Functions for each module to upload their datavault directory
'''
@inlineCallbacks
def updateDataVaultDirectory(window, directory):
    try:
        yield window.serversList['dv'].cd('')
        yield window.serversList['dv'].cd(directory)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
Clear Plots, can take a list/dict or single plot
'''
def ClearPlots(Plotlist):
    if isinstance(Plotlist, list): #Input is a list of plots
        for plot in Plotlist:
            plot.clear()
    elif isinstance(Plotlist, dict): #input is the plotlist
        for PlotName in Plotlist:
            #Plotlist[PlotName]['Layout'].removeWidget(Plotlist[PlotName]['PlotObject'])
            Plotlist[PlotName]['PlotObject'].close()
            if 'ROIPlot' in Plotlist[PlotName]:
                if Plotlist[PlotName]['ROIPlot'] is not None:
                    Plotlist[PlotName]['ROIPlot'].close()
            for counter in range(0,len(Plotlist[PlotName]['PlotData'])): ##clear all the data
            	Plotlist[PlotName]['PlotData'].pop()
            	Plotlist[PlotName]['PlotData'].insert(0,[])
    else:#input is a single plot
        Plotlist.clear()

'''
Input: PlotItem, Layout of Plot and Plot properties
'''
def Setup1DPlot(Plot, Layout, Title, yaxis, yunit, xaxis, xunit):
    Plot.setGeometry(QtCore.QRect(0, 0, 5, 5))
    if Title is not None:
        Plot.setTitle(Title)
    Plot.setLabel('left', yaxis, units = yunit)
    Plot.setLabel('bottom', xaxis, units = xunit)
    Plot.showAxis('right', show = True)
    Plot.showAxis('top', show = True)
    Plot.setXRange(-1, 1) #Default Range
    Plot.setYRange(-1, 1) #Default Range
    Plot.addLegend()
    Plot.enableAutoRange(enable = True)
    Layout.addWidget(Plot)

'''
From Plot List, plot all the data based on the PlotData itt is holding
'''
def RefreshPlot1D(PlotList):
    try:
        for PlotName in PlotList:
            Plot1DData(PlotList[PlotName]['PlotData'][0], PlotList[PlotName]['PlotData'][1], PlotList[PlotName]['PlotObject'])
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)



'''
Input: Data for Xaxis, Yaxis and plot object
'''
def Plot1DData(xaxis, yaxis, plot, color = 0.5, name = '',init = 1):
    if name == '' or init != 0:
        plot.plot(x = xaxis, y = yaxis, pen = color,symbol='o')
    else:
        plot.plot(x = xaxis, y = yaxis, pen = color, name = name,symbol='o')



def Setup2DPlot(Layout, yaxis, yunit, xaxis, xunit):
    PlotItem = pg.PlotItem()
    ImageView = CustomImageView(view = PlotItem)

    PlotItem.setLabel('left', yaxis, units = yunit)
    PlotItem.setLabel('bottom', xaxis, units = xunit)
    PlotItem.showAxis('top', show = True)
    PlotItem.showAxis('right', show = True)
    PlotItem.setAspectLocked(False)
    PlotItem.invertY(False)
    PlotItem.setXRange(-1.0, 1.0)
    PlotItem.setYRange(-1.0, 1.0)

    ImageView.setGeometry(QtCore.QRect(0, 0, 20, 20))
    ImageView.ui.menuBtn.hide()
    ImageView.ui.histogram.item.gradient.loadPreset('bipolar')
    ImageView.ui.roiBtn.hide()
    ImageView.ui.menuBtn.hide()
    Layout.addWidget(ImageView)
    return ImageView

def Connect2DPlots(PlotName, PlotList):
    PlotList[PlotName]['PlotObject'] = Setup2DPlot(PlotList[PlotName]['PlotObject'], PlotList[PlotName]['Layout'], PlotList[PlotName]['YAxisName'], PlotList[PlotName]['YUnit'], PlotList[PlotName]['XAxisName'], PlotList[PlotName]['XUnit'])
    Setup1DPlot(PlotList[PlotName]['YZPlot']['PlotObject'], PlotList[PlotName]['YZPlot']['Layout'], PlotList[PlotName]['YZPlot']['Title'], PlotList[PlotName]['YZPlot']['YAxisName'], PlotList[PlotName]['YZPlot']['YUnit'], PlotList[PlotName]['YZPlot']['XAxisName'], PlotList[PlotName]['YZPlot']['XUnit'])#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
    Setup1DPlot(PlotList[PlotName]['XZPlot']['PlotObject'], PlotList[PlotName]['XZPlot']['Layout'], PlotList[PlotName]['XZPlot']['Title'], PlotList[PlotName]['XZPlot']['YAxisName'], PlotList[PlotName]['XZPlot']['YUnit'], PlotList[PlotName]['XZPlot']['XAxisName'], PlotList[PlotName]['XZPlot']['XUnit'])#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
    PlotList[PlotName]['PlotObject'].addItem(PlotList[PlotName]['YZPlot']['LineCut'], ignoreBounds = True)
    PlotList[PlotName]['YZPlot']['LineCut'].sigPositionChangeFinished.connect(lambda: UpdateLineCutMoving(PlotList[PlotName], 'YZPlot'))
    PlotList[PlotName]['YZPlot']['LineEdit'].editingFinished.connect(lambda: UpdateLineCutLineEdit(PlotList[PlotName], 'YZPlot'))
    PlotList[PlotName]['PlotObject'].addItem(PlotList[PlotName]['XZPlot']['LineCut'], ignoreBounds = True)
    PlotList[PlotName]['XZPlot']['LineCut'].sigPositionChangeFinished.connect(lambda: UpdateLineCutMoving(PlotList[PlotName], 'XZPlot'))
    PlotList[PlotName]['XZPlot']['LineEdit'].editingFinished.connect(lambda: UpdateLineCutLineEdit(PlotList[PlotName], 'XZPlot'))


def Plot2DData(ImageView, Data, Minx, Miny, Scalex, Scaley, autoRange = False, autoLevels = False):
    ImageView.setImage(Data, autoRange = autoRange , autoLevels = autoLevels, pos = [Minx, Miny], scale = [Scalex, Scaley])

def UpdateLineCutMoving(PlotDictionary, LineCutName):
    PlotDictionary[LineCutName]['Value'] = PlotDictionary[LineCutName]['LineCut'].value()
    PlotDictionary[LineCutName]['LineEdit'].setText(formatNum(PlotDictionary[LineCutName]['Value'], 6))
    RefreshLineCutPlot(PlotDictionary, LineCutName, PlotDictionary[LineCutName]['PlotData'])

def UpdateLineCutLineEdit(PlotDictionary, LineCutName):
    dummystr=str(PlotDictionary[LineCutName]['LineEdit'].text())   #read the text
    dummyval=readNum(dummystr, None , False)
    if isinstance(dummyval, float):
        PlotDictionary[LineCutName]['Value'] = float(dummyval)
    PlotDictionary[LineCutName]['LineEdit'].setText(formatNum(PlotDictionary[LineCutName]['Value'], 6))
    RefreshLineCutPlot(PlotDictionary, LineCutName, PlotDictionary[LineCutName]['PlotData'])

def RefreshLineCutPlot(PlotDictionary, LineCutPlotName, PlotData):
    try:
        Value = PlotDictionary[LineCutPlotName]['Value']
        PlotDictionary[LineCutPlotName]['LineCut'].setValue(float(Value))#Move Linecut
        LineCutPlot = PlotDictionary[LineCutPlotName]['PlotObject']
        if LineCutPlotName == 'YZPlot':
            Min, Scale = PlotDictionary['PlotObject'].Position[0], PlotDictionary['PlotObject'].ScaleSize[0]
            XDataMin, XDataScale, NumberofData = PlotDictionary['PlotObject'].Position[1], PlotDictionary['PlotObject'].ScaleSize[1], PlotDictionary['PlotObject'].ImageData.shape[1]
            Index = int((Value - Min) / Scale + 0.5)
            PlotDictionary[LineCutPlotName]['PlotData'][1] = PlotDictionary['PlotData'][:, Index]
        else:
            Min, Scale = PlotDictionary['PlotObject'].Position[1], PlotDictionary['PlotObject'].ScaleSize[1]
            XDataMin, XDataScale, NumberofData = PlotDictionary['PlotObject'].Position[0], PlotDictionary['PlotObject'].ScaleSize[0], PlotDictionary['PlotObject'].ImageData.shape[0]
            Index = int((Value - Min) / Scale + 0.5)
            PlotDictionary[LineCutPlotName]['PlotData'][1] = PlotDictionary['PlotData'][Index]
     
        PlotDictionary[LineCutPlotName]['PlotData'][0] = np.linspace(XDataMin, XDataMin + NumberofData * XDataScale - XDataScale, NumberofData)
        LineCutPlot.clear()
        if LineCutPlotName == 'YZPlot':
            Plot1DData(PlotDictionary[LineCutPlotName]['PlotData'][1], PlotDictionary[LineCutPlotName]['PlotData'][0], LineCutPlot)
        else:
            Plot1DData(PlotDictionary[LineCutPlotName]['PlotData'][0], PlotDictionary[LineCutPlotName]['PlotData'][1], LineCutPlot)
     
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
     
def Division(voltage, current, multiplier = 1):
    if current != 0.0:
        resistance = float(voltage / current) * multiplier
    else:
        resistance = float(voltage / 0.0000000001) * multiplier
    return resistance

def Subtract(InputA, InputB):
    Difference = InputA - InputB
    return Difference

'''
Attach Attach_Data to the front of data
'''
def AttachData_Front(data, attached_data):
    if len(data.shape) == 1: # 1D array
        axisnumber = 0
    else:
        axisnumber = 1
    Data_Combined = np.insert(data, 0, attached_data, axis = axisnumber)
    return Data_Combined

'''
Attach Attach_Data to the back of data
'''
def AttachData_Back(data, attached_data):
    if len(data.shape) == 1: # 1D array
        axisnumber = 0
        column = len(data)
    else:
        axisnumber = 1
        column = data.shape[1]
    Data_Combined = np.insert(data, column, attached_data, axis = axisnumber)
    return Data_Combined

def ReplaceData(data, index, replaced_data):
    Data_Replaced = data
    if len(data.shape) == 1: # 1D array
        Data_Replaced[index] = replaced_data
    else:
        Data_Replaced[:, index] = replaced_data
    return Data_Replaced

def Attach_ResistanceConductance(data, VoltageIndex, CurrentIndex, multiplier = 1):
    try:
        if len(data.shape) == 1: # 1D array
            Voltage, Current = data[VoltageIndex], data[CurrentIndex]
            Resistance = Division(Voltage, Current)
            Conductance = Division(Current, Voltage)
        else:
            Voltage, Current = data[:, VoltageIndex], data[:, CurrentIndex]
            Resistance = np.transpose(map(Division, Voltage, Current))
            Conductance = np.transpose(map(Division, Current, Voltage))
        Data_Attached1 = AttachData_Back(data, Resistance)
        Data_Attached = AttachData_Back(Data_Attached1, Conductance)
        
        return Data_Attached
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
        
def Generate_Difference(data, InputAIndex, InputBIndex, dataIndex):
    try:
        if len(data.shape) == 1: # 1D array
            InputA, InputB = data[InputAIndex], data[InputBIndex]
            Difference = Subtract(InputA, InputB)
        else:
            InputA, InputB = data[:, InputAIndex], data[:, InputBIndex]
            Difference = np.transpose(map(Subtract, InputA, InputB))
        Data_Generated = ReplaceData(data, dataIndex, Difference)
        return Data_Generated
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
        
'''
Multiply array with the input list
'''
def Multiply(Data, Multiplierlist):
    multiplymatrix = np.diag(Multiplierlist)
    MultipliedData = np.dot(Data, multiplymatrix)
    return MultipliedData














'''
nSOT Scanner Session
'''
def formatNum(val, decimal_values = 2):
    if val != val:
        return 'nan'
        
    string = '%e'%val
    ind = string.index('e')
    num  = float(string[0:ind])
    exp = int(string[ind+1:])
    if exp < -6:
        diff = exp + 9
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'n'
    elif exp < -3:
        diff = exp + 6
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'u'
    elif exp < 0:
        diff = exp + 3
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'m'
    elif exp < 3:
        if val - int(val) == 0:
            val = int(val)
        else: 
            val = round(val,decimal_values)
        string = str(val)
    elif exp < 6:
        diff = exp - 3
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'k'
    elif exp < 9:
        diff = exp - 6
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'M'
    elif exp < 12:
        diff = exp - 9
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'G'
    return string
    
#By default, accepts no parent and will warn you for inputting a number without units. 
#Adding a parent is needed to have error thrown in a reasonable place and avoid recursion errors. 
#For entries that are expected to be of order unity the warningFlag can be set to False. 
def readNum(string, parent, warningFlag = True):
    try:
        val = float(string)
        
        if warningFlag and val != 0:
            warning = UnitWarning(parent, val)
            parent.setFocus()
            if warning.exec_():
                pass
            else:
                return 'Rejected Input'
    except:
        try:
            exp = string[-1]
            if exp == 'm':
                exp = 1e-3
            if exp == 'u':
                exp = 1e-6
            if exp == 'n':
                exp = 1e-9
            if exp == 'p':
                exp = 1e-12
            if exp == 'k':
                exp = 1e3
            if exp == 'M':
                exp = 1e6
            if exp == 'G':
                exp = 1e9
            try:
                val = float(string[0:-1])*exp
            except: 
                return 'Incorrect Format'
        except:
            return 'Empty Input'
    return val
        
#---------------------------------------------------------------------------------------------------------#         
""" The following section creates a generic warning if a numebr is input without a unit."""
        
from PyQt5 import QtGui, QtCore, uic
import os

path = os.path.dirname(os.path.realpath(__file__))
Ui_UnitWarning, QtBaseClass = uic.loadUiType(os.path.join(path, "UnitWarningWindow.ui"))
        
class UnitWarning(QtGui.QDialog, Ui_UnitWarning):
    def __init__(self, parent, val):
        super(UnitWarning, self).__init__(parent)
        self.window = parent
        self.setupUi(self)
        
        self.label.setText(self.label.text() + formatNum(val) + '.')
        
        self.push_yes.clicked.connect(self.acceptEntry)
        self.push_no.clicked.connect(self.rejectEntry)
        
    def acceptEntry(self):
        self.accept()
        
    def rejectEntry(self):
        self.reject()
        
    def closeEvent(self, e):
        self.reject()

#---------------------------------------------------------------------------------------------------------#         
""" The following section creates a generic warning."""
        
def ShowWarning(text, parent = None):
    warning = GeneralWarning(parent, text)
    if warning.exec_():
        return True
    else:
        return False

Ui_GeneralWarning, QtBaseClass = uic.loadUiType(os.path.join(path, "GeneralWarningWindow.ui"))
        
class GeneralWarning(QtGui.QDialog, Ui_GeneralWarning):
    def __init__(self, parent, text):
        super(GeneralWarning, self).__init__(parent)
        self.window = parent
        self.setupUi(self)
        
        self.label.setText(text)
        
        self.push_yes.clicked.connect(self.acceptEntry)
        self.push_no.clicked.connect(self.rejectEntry)
        
    def acceptEntry(self):
        self.accept()
        
    def rejectEntry(self):
        self.reject()
        
    def closeEvent(self, e):
        self.reject()













'''
Measurement related code
'''


#Lock-in Measurement Code
'''
Get R from Lock In
'''
@inlineCallbacks
def Get_SR_LI_R(LockInDevice):
    try:
        value = yield LockInDevice.r()
        returnValue(value)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

@inlineCallbacks
def Read_LockIn_TimeConstant(LockInDevice):
    value = yield LockInDevice.time_constant()
    returnValue(value)

@inlineCallbacks
def Set_LockIn_TimeConstant(LockInDevice, value):
    actualvalue = yield LockInDevice.time_constant(value)
    returnValue(actualvalue)

@inlineCallbacks
def Read_LockIn_Frequency(LockInDevice):
    value = yield LockInDevice.frequency()
    returnValue(value)

@inlineCallbacks
def Set_LockIn_Frequency(LockInDevice, value):
    actualvalue = yield LockInDevice.frequency(value)
    returnValue(actualvalue)

#SIM900 Measurement Code
'''
Set SIM900 Voltage Source.
'''
@inlineCallbacks
def Set_SIM900_VoltageOutput(SIM900Device, VoltageSourceSlot, Voltage):
    try:
        yield SIM900Device.dc_set_voltage(VoltageSourceSlot, Voltage)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
Ramp the DACADC without taking data, usually used to ramp to initial voltage. It also require a reactor to sleep asynchronously. Attention: Ramp takes instead of Number of steps, it takes stepsize which is more logical
'''
@inlineCallbacks
def Ramp_SIM900_VoltageSource(SIM900Device, VoltageSourceSlot, StartingVoltage, EndVoltage, StepSize, Delay, reactor = None, c = None):
    try:
        Numberofsteps = abs(StartingVoltage - EndVoltage) / StepSize
        if Numberofsteps < 2:
            Numberofsteps = 2
        for voltage in np.linspace(StartingVoltage, EndVoltage, Numberofsteps):
            yield SIM900Device.dc_set_voltage(VoltageSourceSlot, voltage)
            SleepAsync(reactor, Delay)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

#DACADC Measurement Code
'''
Set DAC Voltage
'''
@inlineCallbacks
def Set_DAC(DACADC_Device, Port, Voltage):
    try:
        yield DACADC_Device.set_voltage(Port, Voltage)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
Read ADC and set label
'''
@inlineCallbacks
def Read_ADC_SetLabel(DACADC_Device, Port, label):
    try:
        voltage = yield Read_ADC(DACADC_Device, Port)
        label.setText(formatNum(voltage, 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

@inlineCallbacks
def Read_DAC_SetLabel(DACADC_Device, Port, label):
    try:
        voltage = yield DACADC_Device.read_dac(Port)
        label.setText(formatNum(voltage, 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)


'''
Read ADC and return value
'''
@inlineCallbacks
def Read_ADC(DACADC_Device, Port):
    try:
        voltage = yield DACADC_Device.read_voltage(Port)
        returnValue(voltage)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
Ramp the DACADC without taking data, usually used to ramp to initial voltage.
'''
@inlineCallbacks
def Ramp_DACADC(DACADC_Device, Port, StartingVoltage, EndVoltage, StepSize, Delay, c = None):
    try:
        if StartingVoltage != EndVoltage:
            Delay = int(Delay * 1000000) #Delay in DAC is in microsecond
            Numberofsteps = int(abs(StartingVoltage - EndVoltage) / StepSize)
            if Numberofsteps < 2:
                Numberofsteps = 2
            g = yield DACADC_Device.ramp1(Port, float(StartingVoltage), float(EndVoltage), Numberofsteps, Delay)
            returnValue(g)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
Buffer_Ramp of DACADC, take the DACADC device object, list of channel output and input along with the min and max, all should be list and number of elements should match.
buffer ramp function can be look up on DACADC server.
'''
@inlineCallbacks
def Buffer_Ramp_DACADC(DACADC_Device, ChannelOutput, ChannelInput, Min, Max, Numberofsteps, Delay,mult = 1):
    try:
        DACDelay = int(Delay*1000000) #This is in unit of microsecond
        data = yield DACADC_Device.buffer_ramp(ChannelOutput,ChannelInput,Min,Max,Numberofsteps,DACDelay)
        #d_read = yield DACADC_Device.serial_poll.future(len(ChannelInput),Numberofsteps)
        #d_tmp = yield d_read.result()
        returnValue(data)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
Debugging version of buffer_ramp. Use it as if it is DAC bufferramp but it does not need to be yielded
'''
def Buffer_Ramp_Debug(Device, Output, Input, Min, Max, NoS, Delay):
    DebugData = []
    xpoints = np.linspace(Min, Max, NoS)
    for i in range(0, len(Input)):
        DebugData.append([])
        for j in xpoints:
            DebugData[i].append(i * j)
    return DebugData

#Magnetic Field control
@inlineCallbacks
def RampMagneticField(DeviceObject, ServerName, TargetField, RampRate, Reactor):
    try:
        if 'IPS120' in ServerName:
            yield DeviceObject.set_control(3)
            yield DeviceObject.set_fieldsweep_rate(RampRate)#Set Ramp Rate
            yield DeviceObject.set_control(2)

            yield DeviceObject.set_control(3)
            yield DeviceObject.set_targetfield(TargetField) #Set the setpoin
            yield DeviceObject.set_control(2)

            yield DeviceObject.set_control(3)
            yield DeviceObject.set_activity(1) #Put ips in go to setpoint mode
            yield DeviceObject.set_control(2)

            print('Setting field to ' + str(TargetField))

            while True:
                yield DeviceObject.set_control(3)#
                current_field = yield DeviceObject.read_parameter(7)#Read the field
                yield DeviceObject.set_control(2)#
                #if within 10 uT of the desired field, break out of the loop
                if float(current_field[1:]) <= TargetField + 0.00001 and float(current_field[1:]) >= TargetField -0.00001:#if reach target field already
                    break
                else:
                #if after one second we still haven't reached the desired field, then reset the field setpoint and activity
                    yield DeviceObject.set_control(3)
                    yield DeviceObject.set_targetfield(TargetField)
                    yield DeviceObject.set_control(2)
                    yield DeviceObject.set_control(3)
                    yield DeviceObject.set_activity(1)
                    yield DeviceObject.set_control(2)
                    print('restarting loop')
                    SleepAsync(Reactor, 0.25)

        if 'AMI430' in ServerName:
            print('Setting field to ' + str(TargetField))
            t0 = time.time() #Keep track of starting time for setting the field
            yield DeviceObject.conf_field_targ(TargetField) #Set targer field
            yield DeviceObject.ramp() #Start ramp
            target_field = yield DeviceObject.get_field_targ()#Get target field set in the device
            actual_field = yield DeviceObject.get_field_mag() #read actual field
            while abs(target_field - actual_field) > 1e-3:
                time.sleep(2)
                actual_field = yield DeviceObject.get_field_mag() #read actual field
    except Exception as inst:
        print('Scan error: ', inst)
        print('on line: ', sys.exc_info()[2].tb_lineno)

#Temperature Control 12/19/19

#returns an array of form [ [T1,T2,T3,T4],[setpoin1,2,3,4], [heateroutput1,2,3,4],[heaterrange1,2,3,4] ]
@inlineCallbacks
def Read_Lakeshore_Status(Lakeshore_Device):
    data = [[0,0,0,0],[0,0],[0,0],[0,0]]
    channel_dict = {1:'A',2:'B',3:'C',4:'D'}
    for channel in range(1,5):
        data[0][channel-1] = yield Lakeshore_Device.read_temp(str(channel_dict[channel]))
        if channel <= 2:
            data[1][channel-1] = yield Lakeshore_Device.read_p(channel)
            data[2][channel-1] = yield Lakeshore_Device.read_heater_output(channel)
            data[3][channel-1] = yield Lakeshore_Device.read_heater_range(channel)
    returnValue(data)

@inlineCallbacks
def Read_Lakeshore_Status_SetLabel(Lakeshore_Device,labels):
    data = yield Read_Lakeshore_Status(Lakeshore_Device)
    outputs = []
    for x in data:
        for y in x:
            outputs.append(str(trimReadValue(y)))
    for counter in range(0,10):
        labels[counter].setText(str(trimReadValue(outputs[counter])))
    returnValue(outputs)

#set ramprates, heaterranges,setpoints
@inlineCallbacks
def Set_Lakeshore_Ramping(Lakeshore_Device,inputs):
    for channel in range(1,3):
        yield Lakeshore_Device.set_ramp(channel,True,inputs[0][channel-1])
        yield Lakeshore_Device.set_heater_range(channel,int(inputs[1][channel-1]))
        yield Lakeshore_Device.set_p(channel,inputs[2][channel-1])


def trimReadValue(string):
    return float(string.rstrip('\\r\\n\'').lstrip('b\'').rstrip('\\n\''))


#set target field and ramp rate for AMI 430
@inlineCallbacks
def Set_AMI(Magnet_Device,inputs):
    yield Magnet_Device.conf_field_units(1) #Use tesla
    yield Magnet_Device.conf_ramp_rate_seg(1) #one segment ramp
    yield Magnet_Device.conf_ramp_rate_units(1)  #time in / min 
    opc_resp = yield Magnet_Device.opcq()
    yield Magnet_Device.conf_field_targ(min(inputs['Target'],inputs['Max_Field']))
    yield Magnet_Device.conf_ramp_rate_field(1,min(inputs['FieldRate'],inputs['Max_Ramp_Rate']),inputs['Max_Field'])
    #opc_resp = yield Magnet_Device.opcq()
    #returnValue(1)

#Pauses the AMI
@inlineCallbacks
def Pause_AMI(Magnet_Device):
	yield Magnet_Device.pause()

#Zeros the AMI
@inlineCallbacks
def Zero_AMI(Magnet_Device):
	yield Magnet_Device.zero()

#Reads the status of the AMI + set the labels
@inlineCallbacks
def Read_AMI_Status_SetLabel(Magnet_Device,labels):
    data = yield Read_AMI_Status(Magnet_Device)
    state_dict = {1: 'RAMPING',2: 'HOLDING',3: 'PAUSED',4: 'MANUAL UP',5: 'MANUAL DOWN',6: 'ZEROING CURRENT',7: 'QUENCH DETECTED',8: 'ZERO',9: 'HEATING PS',10: 'COOLING PS'}
    pswitch_dict = {0: 'OFF', 1: 'ON'}
    persistent_dict = {0: 'NORMAL', 1: 'PERSISTENT MODE ON'}
    for i in range(0, len(labels)):
        if i < 3:
            labels[i].setText(str(data[i]))
        elif i == 3:
            labels[i].setText(state_dict[int(data[i])])
        elif i == 4:
            labels[i].setText(pswitch_dict[int(data[i])])
        elif i == 5:
            labels[i].setText(persistent_dict[int(data[i])])


    returnValue(data)


@inlineCallbacks
def Read_AMI_Status(Magnet_Device):
    data = [0,0,0,0,0,0]
    data[0] = yield Magnet_Device.get_field_mag()#field
    data[1] = yield Magnet_Device.get_ramp_rate_field(1)#rate
    data[2] = yield Magnet_Device.get_field_targ()#target
    data[3] = yield Magnet_Device.state()#status
    data[4] = yield Magnet_Device.get_pswitch() #persistent mode
    data[5] = yield Magnet_Device.get_persistent() #pswitch
    returnValue(data)

#Checks PSwitch on (or turns it on, as long as not in persistent mode) and ramp
@inlineCallbacks
def Ramp_AMI(Magnet_Device):
    ps_state = yield Magnet_Device.get_pswitch()
    if ps_state == 0:
        persistent_mode = yield Magnet_Device.get_persistent()
        if persistent_mode == 0:
            yield Magnet_Device.persistent_switch_on()
    yield Magnet_Device.ramp()

#Enters persistent mode
@inlineCallbacks
def Enter_PMode_AMI(Magnet_Device):
    state = yield Magnet_Device.state()
    if state == 2 or state == 3: #must be holding or paused
        field = yield Magnet_Device.get_field_mag()
        yield Magnet_Device.persistent_switch_off()
        yield Magnet_Device.zero() ##should this be Magnet_Device.zero() instead?
        state = yield Magnet_Device.state()
        while state != 8:
            state = yield Magnet_Device.state()
    elif state == 8:
        yield Magnet_Device.persistent_switch_off()
    returnValue(1)

#Exit persistent mode, or turn on switch if not in persistent mode / switch is off
@inlineCallbacks
def Exit_PMode_AMI(Magnet_Device):
    persistent_mode = yield Magnet_Device.persistent()
    if persistent_mode == 1:
        field = yield Magnet_Device.get_field_mag() # because in persistent mode, will be the field we want
        yield Magnet_Device.conf_field_targ(field)
        yield Magnet_Device.ramp() # I *think* this should automatically be faster
        state = yield Magnet_Device.state()
        while state != 2 and state != 3:
            state = yield Magnet_Device.state()
        if state == 2 or state == 3:
            yield Magnet_Device.persistent_switch_on()

        state = yield Magnet_Device.state()
        if state != 2 and state != 3:
            state = yield Magnet_Device.state()
    elif persistent_mode == 0:
        pswitch_state = yield Magnet_Device.get_pswitch()
        state = yield Magnet_Device.state()
        if pswitch_state == 0 and (state == 3 or state==8):
            yield Magnet_Device.persistent_switch_on()
    returnValue(1)


#Data Vault related Code
'''
Generate Datavault Files, using datavault object, dataname(str), list of dependent variables and independent variables
return the imagenumber and directory number for updating GUI
'''
@inlineCallbacks
def CreateDataVaultFile(datavault, DataName, DependentVariablesList, IndependentVariablesList):
    file = yield datavault.new(DataName, DependentVariablesList, IndependentVariablesList)
    ImageNumber = file[1][0:5]
    session  = ''
    for folder in file[0][1:]:
        session = session + '\\' + folder
    ImageDir = r'\.datavault' + session
    returnValue([ImageNumber, ImageDir])

'''
After creating datavault file, attach parameters to the file
'''
@inlineCallbacks
def AddParameterToDataVault(datavault, parameterdict):
    try:
        for key, value in parameterdict.items():
            yield datavault.add_parameter(key, parameterdict[key])
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

'''
grab screenshot of the window and save the screenshot to sessionfolder
'''
def saveDataToSessionFolder(winId, SessionFolder, ScreenshotName):
    try:
        screen = QApplication.primaryScreen()
        p = screen.grabWindow(winId)

        #p = QtGui.QScreen.grabWindow(winId)
        a = p.save(SessionFolder + '\\' + ScreenshotName + '.jpg','jpg')
        if not a:
            print("Error saving Scan data picture")
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

#General Stuff

"""Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
other operations to be done elsewhere while paused."""
def SleepAsync(reactor, secs):
    d = Deferred()
    reactor.callLater(secs, d.callback, 'Sleeping')
    return d


#ImageView for Plotting Purpose
class CustomImageView(pg.ImageView):
    '''
    Extension of pyqtgraph's ImageView.
    1. histogram ignore 0.0, Quick and Dirt fix of setting histogram to ignore 0.0
    2. Store ImageData, Position and ScaleSize
    3. AutoSetLevels set histogram regardless of 0.0
    '''
    def __init__(self, parent=None, name="ImageView", view=None, imageItem=None, * args):
        pg.ImageView.__init__(self, parent, name, view, imageItem, *args)


    def setImage(self, img, autoRange = False, autoLevels = False, levels = None, axes = None, xvals = None, pos = None, scale = None, transform = None, autoHistogramRange = False):
        try:
            if autoRange:
                self.AutoSetRange(img, pos = [pos[0] - scale[0] / 2, pos[1] - scale[1] / 2], scale = scale)
            self.ImageData = img
            self.Position = pos
            self.ScaleSize = scale
            r0 = np.where(np.all(img == 0.0, axis = 0))[0]
            c0 = np.where(np.all(img == 0.0, axis = 1))[0]
            tmp = np.delete(np.delete(img, r0, axis = 1), c0, axis = 0)
            if np.all(tmp == 0.0) or np.size(tmp) == 0: #Clear if nothing is being plotted 
                pg.ImageView.clear(self)
            else:
                pg.ImageView.setImage(self, tmp, False, False, levels, axes, xvals, [pos[0] - scale[0] / 2, pos[1] - scale[1] / 2], scale, transform, False)
            if autoLevels:
                self.AutoSetLevels()

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
    
    def AutoSetLevels(self):
        ZeroRemoved = self.ImageData[self.ImageData != 0.0]
        Min, Max = np.amin(ZeroRemoved), np.amax(ZeroRemoved)
        if Min == Max:
            Min = Max - 10**-15
        pg.ImageView.setLevels(self, Min, Max)

    def AutoSetRange(self, data, pos, scale): #
        pg.ImageView.setImage(self, data, autoLevels = False, pos = pos, scale = scale)

#Transport methods
def vs_fixed(p0, n0, delta, vs):
    """
    :param p0: polarizing field
    :param n0: charge carrier density
    :param delta: capacitor asymmetry
    :param vs: fixed voltage set on graphene sample
    :return: (v_top, v_bottom)
    """
    return vs + 0.5 * (n0 + p0) / (1.0 + delta), vs + 0.5 * (n0 - p0) / (1.0 - delta)

def vs_fixed_1gate(p0,n0,delta,vs):
    """
    :param p0: polarizing field
    :param n0: charge carrier density
    :param delta: capacitor asymmetry
    :param vs: fixed voltage set on graphene sample
    :return: (v_gate, 0)
    """
    return n0, 0.0*n0


def function_select(s):
    """
    :param s: # of gates
    :return: function f
    """
    if s == 1:
        f = vs_fixed_1gate
    elif s == 2:
        f = vs_fixed
    return f

    
def reshape_data(data,mult):
    """
    this bins and averages the output of the ADC when a higher point density (mult*# of data points)
    is used to make the gate sweep more smooth
    """
    data_reshaped = np.reshape(data,(np.shape(data)[0],np.shape(data)[1]/mult,mult))
    data_reshaped = np.mean(data_reshaped,2)
    return data_reshaped

def mesh(vfixed, offset, drange, nrange, gates=1, pxsize=(100, 100), delta=0.0):
    """
    drange and nrange are tuples (dmin, dmax) and (nmin, nmax)
    offset  is a tuple of offsets:  (N0, D0)
    pxsize  is a tuple of # of steps:  (N steps, D steps)
    fixed sets the fixed channel: "vb", "vt", "vs"
    fast  - fast axis "D" or "N"
    """
    f = function_select(gates)
    p0 = np.linspace(drange[0], drange[1], pxsize[1]) - offset[1]
    n0 = np.linspace(nrange[0], nrange[1], pxsize[0]) - offset[0]
    n0, p0 = np.meshgrid(n0, p0)  # p0 - slow n0 - fast
    # p0, n0 = np.meshgrid(p0, n0)  # p0 - slow n0 - fast
    v_fast, v_slow = f(p0, n0, delta, vfixed)
    return np.dstack((v_fast, v_slow)), np.dstack((p0, n0))

@inlineCallbacks
def createDVClient(dvplotter,cxn_pointer):
    if cxn_pointer is False:
        from labrad.wrappers import connectAsync
        cxn_pointer = yield connectAsync(host = '127.0.0.1', password='sSET2018')
        dvplotter.localcxn = cxn_pointer
        dv = cxn_pointer.data_vault
        dvplotter.dv = dv
        reg = cxn_pointer.registry
        yield reg.cd('')
        yield reg.cd(['Servers','Data Vault','Repository'])
        settinglist = yield reg.dir()
        osDVFolder = yield reg.get(settinglist[1][-1])
        osDVFolder = osDVFolder.replace('/','\\')
        dvplotter.dvfolder = osDVFolder
        dvplotter.osDVFolder = osDVFolder
        dvplotter.label_DVFolder.setText(dvplotter.dvfolder)
        print('DV Connected')
        dvplotter.Refreshinterface()

#takes in data in terms of lists of points (x,y,z) as individual lists, creates a 2d array of the data for plotting
def CreateImage(x_data,y_data,z_data,x_points,y_points,interp_type):
    xy_points = np.array([x_data, y_data]).T
    if x_points == 0:
        xtot = len(set(xy_points[:,0]))
        x_points = xtot
    if y_points == 0:
        ytot = len(set(xy_points[:,1]))
        y_points = ytot

    xmax = max(xy_points[:,0])
    xmin = min(xy_points[:,0])
    ymax = max(xy_points[:,1])
    ymin = min(xy_points[:,1])
    xgrid, ygrid = np.meshgrid(np.linspace(xmin,xmax,x_points),np.linspace(ymin,ymax,y_points))

    data = griddata(xy_points,np.array(z_data),(xgrid,ygrid),method=interp_type,fill_value = 0)
    
    xspacing = (xmax - xmin) / (x_points + 1)
    yspacing = (ymax - ymin) / (y_points + 1)
    return data,xmin, ymin, xspacing,yspacing


'''The following set of functions deals with reading in a custom string variable'''
def stringdivision(strlist, oplist):
    for element in oplist:
        newlist = []
        for substring in strlist:
            splitlist = substring.split(element)
            for i in range(0,len(splitlist)):
                newlist.append(splitlist[i])
                if i < len(splitlist)-1:
                    newlist.append(element)
        strlist = newlist
    return strlist

def evaluate(delim, location, variable_list,row):
    a = delim[location-1]
    b = delim[location+1]
    if a  in variable_list:
        a = row[variable_list.index(a)]
    else:
        a = float(a)
    if b in variable_list:
        b = row[variable_list.index(b)]
    else:
        b = float(b)
    return [a,b]

def customstringread(input_string,variable_list,op_list):
    string = input_string
    string = string.replace(' ','')
    strlist = [string]
    processed_list = stringdivision(strlist, op_list)
    try:
        leftp_loc = processed_list.index('(')
        rightp_loc = processed_list.index(')')
        sublist = processed_list[leftp_loc:rightp_loc+1]
    except:
        sublist = []
    
    def desired_function(row,plist):
        exp_loc = -2
        while exp_loc != -1:
            try:
                exp_loc = plist.index('^')
                result = evaluate(plist,exp_loc,variable_list,row)
                total = result[0]**result[1]
                plist.insert(exp_loc+2,total)
                plist.pop(exp_loc-1)
                plist.pop(exp_loc-1)
                plist.pop(exp_loc-1)
            except:
                exp_loc = -1
        mult_loc = -2
        while mult_loc != -1:
            try:
                mult_loc = plist.index('*')
                result = evaluate(plist,mult_loc,variable_list,row)
                total = result[0]*result[1]
                plist.insert(mult_loc+2,total)
                plist.pop(mult_loc-1)
                plist.pop(mult_loc-1)
                plist.pop(mult_loc-1)
            except:
                mult_loc = -1
        div_loc = -2
        while div_loc != -1:
            try:
                div_loc = plist.index('/')
                result = evaluate(plist,div_loc,variable_list,row)
                total = result[0]/result[1]
                plist.insert(div_loc+2,total)
                plist.pop(div_loc-1)
                plist.pop(div_loc-1)
                plist.pop(div_loc-1)
            except:
                div_loc  = -1
        sum_loc = -2
        while sum_loc != -1:
            try:
                sum_loc = plist.index('+')
                result = evaluate(plist,sum_loc,variable_list,row)
                total = result[0]+result[1]
                plist.insert(sum_loc+2,total)
                plist.pop(sum_loc-1)
                plist.pop(sum_loc-1)
                plist.pop(sum_loc-1)
            except:
                sum_loc  = -1
        min_loc = -2
        while min_loc != -1:
            try:
                min_loc = plist.index('-')
                result = evaluate(plist,min_loc,variable_list,row)
                total = result[0]-result[1]
                plist.insert(min_loc+2,total)
                plist.pop(min_loc-1)
                plist.pop(min_loc-1)
                plist.pop(min_loc-1)
            except:
                min_loc  = -1

        if len(plist) == 1:
            return plist[0]
        else:
            return plist[1]
    
    return desired_function,processed_list,sublist
    
def loopCustom(variable_list,op_list,array,customstring):
    result_list = []
    for row in array:
        s, plist, slist = customstringread(customstring,variable_list,op_list)
        if slist == []:
            result = s(row,plist)
        else:
            leftp_loc = plist.index('(')
            rightp_loc = plist.index(')')
            sub = (s(row,slist))
            plist[leftp_loc:rightp_loc+1] = [sub]
            plist.remove('')
            plist.remove('')
            result = s(row,plist)
        result_list.append(result)
    return result_list

def addROIPlot(Plotlist,ROIObj,combobox,hold_label):
    #Plotlist['2DPlot']['ROI'] = pg.ROI([0,0],pen='r')
    #Plotlist['2DPlot']['ROI'].addTranslateHandle((0,0),(0,0))
    #Plotlist['2DPlot']['ROI'].addScaleHandle((1,1),(0,0))
    #Plotlist['2DPlot']['PlotObject'].addItem(Plotlist['2DPlot']['ROI'])
    #ROIObj.pos = [Plotlist['2DPlot']['Minx'],Plotlist['2DPlot']['Miny']]
    #print(ROIObj.pos)
    #ROIObj.size = [Plotlist['2DPlot']['XAxisScale'] * 3, Plotlist['2DPlot']['YAxisScale'] * 3]
    if Plotlist['2DPlot']['ROIPlot'] == None:
        Plotlist['2DPlot']['PlotObject'].addItem(ROIObj)
        Plotlist['2DPlot']['ROIPlot'] = pg.PlotWidget()
        ROIObj.setPos([Plotlist['2DPlot']['Minx'],Plotlist['2DPlot']['Miny']])
        ROIObj.setSize([Plotlist['2DPlot']['XAxisScale'] * 3, Plotlist['2DPlot']['YAxisScale'] * 3])
    else: 
        Plotlist['2DPlot']['ROIPlot'].clear()
    hold_dir = combobox.currentText()
    if hold_dir == Plotlist['2DPlot']['XAxisName']:
        Setup1DPlot(Plotlist['2DPlot']['ROIPlot'], Plotlist['2DPlot']['Layout'], '1D Line Cut', Plotlist['2DPlot']['Title'],Plotlist['2DPlot']['ZUnit'],Plotlist['2DPlot']['YAxisName'],Plotlist['2DPlot']['YUnit'])
        ROIObj.snapSize = 0.5*Plotlist['2DPlot']['XAxisScale']
    if hold_dir == Plotlist['2DPlot']['YAxisName']:
        Setup1DPlot(Plotlist['2DPlot']['ROIPlot'], Plotlist['2DPlot']['Layout'], '1D Line Cut', Plotlist['2DPlot']['Title'],Plotlist['2DPlot']['ZUnit'],Plotlist['2DPlot']['XAxisName'],Plotlist['2DPlot']['XUnit'])
        ROIObj.snapSize = 0.5*Plotlist['2DPlot']['YAxisScale']
    Plotlist['2DPlot']['ROIPlot'].enableAutoRange(enable = True)

    updateROIPlot(Plotlist,ROIObj,combobox,hold_label)

    ROIObj.sigRegionChanged.connect(lambda: updateROIPlot(Plotlist,ROIObj,combobox,hold_label))

def updateROIPlot(Plotlist,ROIObj,hold_dir,hold_label):
    minx = Plotlist['2DPlot']['Minx']
    miny = Plotlist['2DPlot']['Miny']
    if Plotlist['2DPlot']['ROIPlot'] is not None:
        Plotlist['2DPlot']['ROIPlot'].clear()
        roiData, roicoords = ROIObj.getArrayRegion(Plotlist['2DPlot']['Imagedata'], Plotlist['2DPlot']['PlotObject'].imageItem,returnMappedCoords=True,axes=(0,1))
        hold_dir = hold_dir.currentText()
        if hold_dir == Plotlist['2DPlot']['XAxisName']:
            roiData = np.mean(roiData,axis=0)
            Plotlist['2DPlot']['ROIPlot'].plot(roicoords[1,0,:]+miny,roiData,symbol='o')
            mean = np.mean(roicoords[0,:,0]+minx)
            str_label = hold_dir + ' = ' + str(mean)
            hold_label.setText(str_label)
        if hold_dir == Plotlist['2DPlot']['YAxisName']:
            roiData = np.mean(roiData,axis=1)
            Plotlist['2DPlot']['ROIPlot'].plot(roicoords[0,:,0]+minx, roiData,symbol='o')
            mean = np.mean(roicoords[1,0,:]+miny)
            str_label = hold_dir + ' = ' + str(mean)
            hold_label.setText(str_label)

def closeROIPlot(Plotlist, ROIObj):
    Plotlist['2DPlot']['ROIPlot'].close()
    Plotlist['2DPlot']['ROIPlot'] = None

def save2DPlot(dvplotter, plotlist):
    filename, a = QtGui.QFileDialog.getSaveFileName(dvplotter,'2DPlot Output File',os.getcwd(),'*.csv')
    filename = str(filename)
    #filename = filename.replace('/','\\')
    print(filename)
    with open(filename, 'w',newline= '\n') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        PlotData = plotlist['2DPlot']['Imagedata']
        for row in PlotData:
            csvwriter.writerow(row)
    csvfile.close()

def saveWindow(dvplotter):
    filename, a = QtGui.QFileDialog.getSaveFileName(dvplotter,'2DPlot Output File','C:\\Users\\Feldman Lab','*.png')
    f = dvplotter.grab()
    f.save(filename)

def ReadInstrumentSetting(busDictionary,deviceName,InstrumentDictionary,sequentialFunction):
    busDictionary[deviceName] = InstrumentDictionary
    sequentialFunction()

def openWindowServers(window,servers,devices):
    window.Servers = servers
    window.Devices = devices
    window.clearInfo()
    window.show()
    window.moveDefault()
    window.raise_()

def SetComboBox_Parameter(dictionary,key,text,refreshFunc = None):
    dictionary[key] = str(text)
    if refreshFunc is not None:
        refreshFunc()

def openEditInstrumentWindow(window,servers,devices,info_dict):
    window.Servers = servers
    window.Devices = devices
    window.InstrumentDict = info_dict
    window.initialize(info_dict)
    window.show()
    window.moveDefault()
    window.raise_()

@inlineCallbacks
def ReadLakeshoreInstrumentSetting(instrumentDict):
    Lakeshore_Device = instrumentDict['DeviceObject']
    if instrumentDict['Measurement'] == 'Input':
        ch1 = yield Lakeshore_Device.read_temp(str(instrumentDict['TempCh1']))
        ch2 = yield Lakeshore_Device.read_temp(str(instrumentDict['TempCh2']))
        returnValue([float(trimReadValue(ch1)),float(trimReadValue(ch2))])
    elif instrumentDict['Measurement'] == 'Output':
        returned_val = yield Lakeshore_Device.read_p(int(instrumentDict['OutputLoop']))
        returnValue([float(trimReadValue(returned_val))])

@inlineCallbacks
def ReadSR830InstrumentSetting(instrumentDict):
    meas_type = instrumentDict['Measurement'] #this should be 'SR830' or 'DACADC'
    quad = instrumentDict['LIReading']
    if meas_type == 'SR830':
        lock_in = instrumentDict['DeviceObject']
        mode = yield lock_in.input_mode()
        output = []
        if quad == 'X/Y':
            x = yield lock_in.x()
            y = yield lock_in.y()
            if mode<2:
                output = [x['V'],y['V']]
            elif mode >= 2:
                output = [x['A'],y['A']]
        elif quad == 'R/T':
            x = yield lock_in.r()
            y = yield lock_in.theta()
            if mode < 2:
                output = [x['V'],y['deg']]
            elif mode >= 2:
                output = [x['A'],y['deg']]
        returnValue(output)
    elif meas_type == 'DACADC':
        dac = instrumentDict['DACADCDeviceObject']
        dac_chx = int(instrumentDict['DACADCChannelX'])
        dac_chy = int(instrumentDict['DACADCChannelY'])
        x_val = yield dac.read_voltage(dac_chx)
        y_val = yield dac.read_voltage(dac_chy)
        x_val = x_val/10 * instrumentDict['Sensitivity']
        y_val = y_val/10 * instrumentDict['Sensitivity']
        returnValue([x_val,y_val])

def ReadSR830fromAbs(voltage,instrumentDict):
    return voltage/10*instrumentDict['Sensitivity']

@inlineCallbacks
def ReadDACADCInstrumentSetting(instrumentDict):
    meas_type = instrumentDict['Measurement'] #this should be 'Input' or 'Output'
    dac = instrumentDict['DeviceObject']
    if meas_type == 'Input':
        adc_ch = int(instrumentDict['ADC Input'])
        value = yield dac.read_voltage(adc_ch)
        returnValue([value])
    elif meas_type == 'Output':
        dac_ch = int(instrumentDict['DAC Output'])
        value = yield dac.read_dac(dac_ch)
        returnValue([value])

@inlineCallbacks
def WriteDACADCInstrumentSetting(instrumentDict,voltage_set): #port should input "Top" or "Bottom"
    dac = instrumentDict['DeviceObject']
    if instrumentDict['Measurement'] == 'Output':
        port = instrumentDict['DAC Output']
        port = int(port) # now should be 0,1
        current_voltage = yield dac.read_dac(port)
        yield Ramp_DACADC(dac,port,current_voltage,voltage_set,.1,.1)
        returnValue(1)


@inlineCallbacks
def WriteLakeshoreInstrumentSetting(instrumentDict,setpoint):
    Lakeshore_Device = instrumentDict['DeviceObject']
    if instrumentDict['Measurement'] == 'Output':
        loop =int(instrumentDict['OutputLoop'])
        htrrange = int(instrumentDict['HeaterRange'])
        feedback = str(instrumentDict['FeedbackCh'])
        yield Lakeshore_Device.set_ramp(loop,True,float(instrumentDict['RampRate']))
        yield Lakeshore_Device.set_heater_range(loop,htrange)
        yield Lakeshore_Device.set_p(loop,setpoint)
        temp = yield Lakeshore_Device.read_temp(feedback)
        tempset = np.zeros(20)
        flag = False
        while flag == False: ## this is arbitrary
            for k in range(0,len(tempset)):
                tempset[k] = abs((yield Lakeshore_Device.read_temp(feedback)) - setpoint)
            if max(tempset) < .1:
                flag = True

def clearLayout(layout):
  while layout.count():
    child = layout.takeAt(0)
    if child.widget():
      child.widget().deleteLater()

#parameter BufferRamp, which is passed in as 0, 1, 2 - 0 if buffer ramp is not to be used;
#1 if 1D buffer Ramp is to be used, 2 if 2D bufferramp is to be used.
@inlineCallbacks
def RecursiveLoop(instrumentBus,looplist,queryfunction,datavault,sweeper,wait,reactor,BufferRamp,variables,delta,progressbar):
    if len(looplist) == 0 and sweeper.flag:
        yield SleepAsync(reactor, wait)
        indep_vals, dep_vals, custom_vals = yield queryfunction()
        yield datavault.add(indep_vals+dep_vals+custom_vals) 
        progressbar.setValue(progressbar.value()+1)
    elif sweeper.flag:
        steps = int(looplist[0][3])
        start = looplist[0][1]
        end = looplist[0][2]
        stepsize = float(end-start)/steps
        instrument = looplist[0][0]
        if (BufferRamp != 1 and BufferRamp != 2) or (len(looplist) > 1 and BufferRamp == 1) or (len(looplist)>2 and BufferRamp == 2):
            for k in range(0,steps+1):
                g = yield instrumentBus[instrument]['WriteFn'](instrumentBus[instrument], start + k*stepsize)

                #add some if statement for a magnet or temperature loop here, have to wait for a given amount of time if so. 
                #alternatively, could include this waittime in 'writefn' for these instruments
                yield RecursiveLoop(instrumentBus,looplist[1:],queryfunction,datavault,sweeper,wait,reactor, BufferRamp,variables,delta,progressbar)
        if BufferRamp == 1 and len(looplist) == 1:
            yield BufferRampSingle(instrumentBus,looplist,queryfunction,datavault,sweeper.flag,wait,reactor,variables,progressbar)
        if BufferRamp == 2 and len(looplist) == 2:
            yield BufferRamp2D(instrumentBus,looplist,queryfunction,datavault,sweeper.flag,wait,reactor,variables,delta,progressbar)

@inlineCallbacks
def BufferRampSingle(instrumentBus,looplist,queryfunction,datavault,flag,wait,reactor,variables,progressbar):
    instrument = looplist[0][0]
    vstart = [looplist[0][1]]
    vstop = [looplist[0][2]]
    steps = int(looplist[0][3])
    indep_vals, dep_vals, custom_vals = yield queryfunction()
    values = indep_vals + dep_vals + custom_vals
    #print(values)
    d_tmp = yield Buffer_Ramp_DACADC(instrumentBus[instrument]['DeviceObject'],[int(instrumentBus[instrument]['DAC Output'])],[0,1,2,3],vstart,vstop,steps+1,wait,mult=1)
    array = np.zeros(((steps+1),len(values)))
    for counter in range(0,len(variables)):
        instrumentName = variables[counter].split('_')[0]
        hit = False
        if instrumentName != 'timestamp': #doesn't correspond to an instrument

            if instrumentName == instrument: #i.e. this is the sweep variable
                hit = True
                array[:,counter] = np.linspace(vstart[0],vstop[0],steps+1)
            elif instrumentBus[instrumentName]['InstrumentType'] == 'DAC-ADC':
                if instrumentBus[instrumentName]['Device'] == instrumentBus[instrument]['Device']:
                    if instrumentBus[instrumentName]['Measurement'] == 'Input':
                        hit = True
                        adc_port = int(instrumentBus[instrumentName]['ADC Input'])
                        array[:,counter] = d_tmp[adc_port]
            elif instrumentBus[instrumentName]['InstrumentType'] == 'SR830':
                if instrumentBus[instrumentName]['Measurement'] == 'DACADC':
                    print('sr hit')
                    hit = True
                    if 'X' or 'R' in variables[counter]:
                        adc_port = int(instrumentBus[instrumentName]['DACADCChannelX'])
                        array[:,counter] = d_tmp[adc_port]/10*instrumentBus[instrumentName]['Sensitivity']
                    elif 'Y' or 'T' in variables[counter]:
                        adc_port = int(instrumentBus[instrumentName]['DACADCChannelY'])
                        array[:,counter] = d_tmp[adc_port]/10*instrumentBus[instrumentName]['Sensitivity']
        if hit == False and counter < len(indep_vals) + len(dep_vals): # variable not measured over BufferRamp
            array[:,counter] = values[counter]
        elif counter >= len(indep_vals)+len(dep_vals):
            custom_bus = instrumentBus[variables[counter]]
            array[:,counter] = custom_bus['CustomFn'](custom_bus,variables,array)
            #for k in range(0,steps):
                #array[k,counter] = custom_bus['CustomFn'](custom_bus,variables,array[k,:])[0]

    progressbar.setValue(progressbar.value()+steps)

    datavault.add(array)


@inlineCallbacks #in 'looplist', take outer loop (i.e. 0) to be bounds on p0, inner (i.e. 1) to be bounds on n0
def BufferRamp2D(instrumentBus,looplist,queryfunction,datavault,flag,wait,reactor,variables,delta,progressbar):
    X_MIN = -10
    X_MAX = 10
    Y_MIN = -10
    Y_MAX = 10
    device_obj = instrumentBus[looplist[0][0]]['DeviceObject']
    pxsize = (int(looplist[1][3]),int(looplist[0][3]))
    extent = (looplist[1][1],looplist[1][2],looplist[0][1],looplist[0][2])
    num_x = pxsize[0] # number of points for n0
    num_y = pxsize[1] # number of points for p0

    #set up plotting for p0,n0
    try:
        datavault.add_parameter('n0_pnts',num_x)
        datavault.add_parameter('n0_rng',(extent[0],extent[1]))
        datavault.add_parameter('p0_pnts',num_y)
        datavault.add_parameter('p0_rng',(extent[2],extent[3]))
    except Exception:
        pass

    DELAY_MEAS = wait
    m,mdn = mesh(0.0,offset = (0,0),drange = (extent[2],extent[3]),nrange=(extent[0],extent[1]),gates=2,pxsize=pxsize,delta=delta)
    inst_1 = looplist[1][0]
    inst_2 = looplist[0][0]
    dac_ch = [int(instrumentBus[looplist[1][0]]['DAC Output']),int(instrumentBus[looplist[0][0]]['DAC Output'])]
    adc_ch = [0,1,2,3]
    for i in range(num_y):
        vec_x = m[i,:][:,0]
        vec_y = m[i,:][:,1]
        md = mdn[i,:][:,0]
        mn = mdn[i,:][:,1]
        mask = np.logical_and(np.logical_and(vec_x <= X_MAX, vec_x >= X_MIN),
            np.logical_and(vec_y <= Y_MAX, vec_y >= Y_MIN))
        if np.any(mask == True):
            start,stop = np.where(mask == True)[0][0],np.where(mask==True)[0][-1]
            yield Ramp_DACADC(device_obj,dac_ch[0],0,vec_x[start],.1,.1)
            yield Ramp_DACADC(device_obj,dac_ch[1],0,vec_y[start],.1,.1)


            vstart = [vec_x[start],vec_y[start]]
            vstop = [vec_x[stop],vec_y[stop]]
            yield SleepAsync(reactor,wait*2)
            
            indep_vals, dep_vals,custom_vals = yield queryfunction()
            indep_vals.append(0) #dummy variable for p0
            indep_vals.append(0) #dummy variable for n0
            values = indep_vals + dep_vals + custom_vals

            num_points = stop - start + 1
            d_tmp = yield Buffer_Ramp_DACADC(device_obj,dac_ch,adc_ch,vstart,vstop,int(num_points),DELAY_MEAS,mult=1)
            array = np.zeros((num_points,len(values)))

            for counter in range(0,len(variables)):
                instrumentName = variables[counter].split('_')[0]
                hit = False
                if instrumentName != 'timestamp' and instrumentName != 'p0' and instrumentName != 'n0': #doesn't correspond to an instrument

                    if instrumentName == inst_1: #i.e. this is the sweep variable
                        hit = True
                        array[:,counter] = np.linspace(vstart[0],vstop[0],num_points)
                    elif instrumentName == inst_2:
                        hit = True
                        array[:,counter] = np.linspace(vstart[1],vstop[1],num_points)
                    elif instrumentBus[instrumentName]['InstrumentType'] == 'DAC-ADC':
                        if instrumentBus[instrumentName]['Device'] == instrumentBus[inst_1]['Device']:
                            if instrumentBus[instrumentName]['Measurement'] == 'Input':
                                hit = True
                                adc_port = int(instrumentBus[instrumentName]['ADC Input'])
                                array[:,counter] = d_tmp[adc_port]
                    elif instrumentBus[instrumentName]['InstrumentType'] == 'SR830':
                        if instrumentBus[instrumentName]['Measurement'] == 'DACADC':
                            hit = True
                            if 'X' in variables[counter]:
                                adc_port = int(instrumentBus[instrumentName]['DACADCChannelX'])
                                array[:,counter] = d_tmp[adc_port]/10*instrumentBus[instrumentName]['Sensitivity']
                            elif 'Y' in variables[counter]:
                                adc_port = int(instrumentBus[instrumentName]['DACADCChannelY'])
                                array[:,counter] = d_tmp[adc_port]/10*instrumentBus[instrumentName]['Sensitivity']
                if instrumentName == 'p0':
                    hit = True
                    array[:,counter] = md
                elif instrumentName == 'n0':
                    hit = True
                    array[:,counter] = mn
                if hit == False and counter < len(indep_vals) + len(dep_vals): # variable not measured over BufferRamp
                    array[:,counter] = values[counter]
                elif counter >= len(indep_vals) + len(dep_vals):
                    custom_bus = instrumentBus[variables[counter]]
                    array[:,counter] = custom_bus['CustomFn'](custom_bus,variables,array)

            progressbar.setValue(progressbar.value()+num_points)
            yield datavault.add(array) #need to figure out a way to save md and mn as well
            yield Ramp_DACADC(device_obj,dac_ch[0],vec_x[stop],0,.1,.1)
            yield Ramp_DACADC(device_obj,dac_ch[1],vec_y[stop],0,.1,.1)

#special version of above function that determines which units to use for SR830 lockin sens
@inlineCallbacks
def ReadEdit_Parameter_LI_Sens(Function, Parameter, parametername, lineEdit,LI):
    try:
        value = yield Function()
        mode = yield LI.input_mode()
        if mode < 2:
            unit = 'V'
        else:
            unit = 'A'
        Parameter[parametername] = value[unit]
        lineEdit.setText(formatNum(Parameter[parametername], 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)


@inlineCallbacks
def SetEdit_Parameter_LI_Sens(Function, Parameter, parametername, lineEdit,LI,unit1,unit2):
    try:
        dummyval = readNum(str(lineEdit.text()), None , False)
        mode = yield LI.input_mode()
        if mode < 2:
            unit = unit1
        else:
            unit = unit2
        value = yield Function(dummyval*unit)
        Parameter[parametername] = value[unit]
        lineEdit.setText(formatNum(Parameter[parametername], 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

def runDVPlotter():
    try:
        dvplotter_file = open('.\\dvplotter_output.txt','w')
        subprocess.Popen(['python',"C:\\Users\\Feldman Lab\\code\\github\\feldmanlab\\Data-Vault-Plotter\\dataVaultLivePlotter.py"],stdout=dvplotter_file,stderr = subprocess.STDOUT)
        print('DV Plotter Open')
    except Exception as inst:
        print('DV Plotter Failed to open')
        print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

@inlineCallbacks
def PingLM(LMDeviceObject,labelslist,reactor,dv = None):
    yield LMDeviceObject.turn_on()
    yield SleepAsync(reactor, 10)
    he_level = yield LMDeviceObject.get_percent()
    timestamp = time.asctime()
    yield LMDeviceObject.turn_off()
    labelslist[0].setText(str(he_level))
    labelslist[1].setText(str(timestamp))


def create_file_LM(dv, data_dir, **kwargs): # try kwarging the vfixed
    try:
        dv.cd('')
        dv.cd(['',data_dir])
    except Exception:
        dv.cd([''])
        dv.mkdir(['',data_dir])
        print("Folder {} was created".format(data_dir))
        dv.cd(['',data_dir])

    ptr = dv.new_ex(str(date.today()), [('Time',[1],'t',''),('Percent',[1],'v','')],'')
    return int(ptr[1][0:5])
