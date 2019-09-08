import numpy as np
from itertools import product
import sys
import twisted
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
import pyqtgraph as pg
#import exceptions
import time
from PyQt5 import QtCore, QtGui

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
def ReadEdit_Parameter(Function, Parameter, parametername, lineEdit):
    try:
        value = yield Function()
        Parameter[parametername] = value
        lineEdit.setText(formatNum(Parameter[parametername], 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

'''
Set a funnction and update a lineEdit
'''
@inlineCallbacks
def SetEdit_Parameter(Function, Parameter, parametername, lineEdit):
    try:
        dummyval = readNum(str(lineEdit.text()), None , False)
        value = yield Function(dummyval)
        Parameter[parametername] = value
        lineEdit.setText(formatNum(Parameter[parametername], 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)
'''
Update parameter, normally just text
Input: dictionary of parameters, key for the value to be changed, the lineEdit where the input comes from
Output: Change the parameter
'''
def UpdateLineEdit_String(parameterdict, key, lineEdit):
    parameterdict[key] = str(lineEdit[key].text())

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
def SelectServer(DeviceList, DeviceName, Serverlist, ServerName):
    try:
        if str(ServerName) != '':#Avoid Select Server when combobox is reconstructed
            DeviceList[str(DeviceName)]['ServerObject'] = Serverlist[str(ServerName)]
            RedefineComboBox(DeviceList[str(DeviceName)]['ComboBoxDevice'], DeviceList[str(DeviceName)]['ServerObject'])
            RefreshIndicator(DeviceList[str(DeviceName)]['ServerIndicator'], DeviceList[str(DeviceName)]['ServerObject'])
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
                print('Connection to ' + device +  ' failed: ', inst, ' on line: ', sys.exc_traceback.tb_lineno)
                DeviceList[str(DeviceName)]['DeviceObject'] = False
        else:
            DeviceList[str(DeviceName)]['DeviceObject'] = False
        RefreshIndicator(DeviceList[str(DeviceName)]['DeviceIndicator'], DeviceList[str(DeviceName)]['DeviceObject'])
        if not SequentialFunction is None:
            SequentialFunction()
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
def RedefineComboBox(combobox, server, reconnect = True):
    try:
        if server != False:
            itemlist = yield QueryDeviceList(server)
        else:
            itemlist = []
        itemlist = ['Offline'] + itemlist
        if len(itemlist) != 1:
            defaultdevice = itemlist[1]
            defaultindex = 1
        else:
            defaultdevice = 'Offline'
            defaultindex = 0
        ReconstructComboBox(combobox, itemlist)
        if reconnect:
            combobox.setCurrentIndex(defaultindex)#This part change the index which should be connect to select device.
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

'''
given a list of item names and populate that into combobox
'''
def ReconstructComboBox(combobox, list):
    combobox.clear()
    for name in list:
        combobox.addItem(name)

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
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

'''
Clear Plots, can take a list/dict or single plot
'''
def ClearPlots(Plotlist):
    if isinstance(Plotlist, list): #Input is a list of plots
        for plot in Plotlist:
            plot.clear()
    elif isinstance(Plotlist, dict): #input is the plotlist
        for PlotName in Plotlist:
            Plotlist[PlotName]['PlotObject'].clear()
    else:#input is a single plot
        Plotlist.clear()

'''
Input: PlotItem, Layout of Plot and Plot properties
'''
def Setup1DPlot(Plot, Layout, Title, yaxis, yunit, xaxis, xunit):
    Plot.setGeometry(QtCore.QRect(0, 0, 10, 10))
    if Title is not None:
        Plot.setTitle(Title)
    Plot.setLabel('left', yaxis, units = yunit)
    Plot.setLabel('bottom', xaxis, units = xunit)
    Plot.showAxis('right', show = True)
    Plot.showAxis('top', show = True)
    Plot.setXRange(-1, 1) #Default Range
    Plot.setYRange(-1, 1) #Default Range
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
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)



'''
Input: Data for Xaxis, Yaxis and plot object
'''
def Plot1DData(xaxis, yaxis, plot, color = 0.5):
    plot.plot(x = xaxis, y = yaxis, pen = color)


def Setup2DPlot(ImageView, Layout, yaxis, yunit, xaxis, xunit):
    PlotItem = pg.PlotItem()
    ImageView = CustomImageView(view = PlotItem)
    PlotItem.setLabel('left', yaxis, units = yunit)
    PlotItem.setLabel('bottom', xaxis, units = xunit)
    PlotItem.showAxis('top', show = True)
    PlotItem.showAxis('right', show = True)
    PlotItem.setAspectLocked(False)
    PlotItem.invertY(False)
    PlotItem.setXRange(-1.0, 1.0, 0)
    PlotItem.setYRange(-1.0, 1.0, 0)
    ImageView.setGeometry(QtCore.QRect(0, 0, 10, 10))
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
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)
     
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
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)
        
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
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)
        
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
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

#DACADC Measurement Code
'''
Set DAC Voltage
'''
@inlineCallbacks
def Set_DAC(DACADC_Device, Port, Voltage):
    try:
        yield DACADC_Device.set_voltage(Port, Voltage)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

'''
Read ADC and set label
'''
@inlineCallbacks
def Read_ADC_SetLabel(DACADC_Device, Port, label):
    try:
        voltage = yield Read_ADC(DACADC_Device, Port)
        label.setText(formatNum(voltage, 6))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

'''
Read ADC and return value
'''
@inlineCallbacks
def Read_ADC(DACADC_Device, Port):
    try:
        voltage = yield DACADC_Device.read_voltage(Port)
        returnValue(voltage)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
            yield DACADC_Device.ramp1(Port, float(StartingVoltage), float(EndVoltage), Numberofsteps, Delay)
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

'''
Buffer_Ramp of DACADC, take the DACADC device object, list of channel output and input along with the min and max, all should be list and number of elements should match.
buffer ramp function can be look up on DACADC server.
'''
@inlineCallbacks
def Buffer_Ramp_DACADC(DACADC_Device, ChannelOutput, ChannelInput, Min, Max, Numberofsteps, Delay):
    try:
        DACDelay = int(Delay * 1000000)#This is in unit of microsecond
        data = yield DACADC_Device.buffer_ramp(ChannelOutput,ChannelInput,Min,Max,Numberofsteps,DACDelay)
        returnValue(np.transpose(data))
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
        print('on line: ', sys.exc_traceback.tb_lineno)


#Data Vault related Code
'''
Generate Datavault Files, using datavault object, dataname(str), list of dependent variables and independent variables
return the imagenumber and directory number for updating GUI
'''
@inlineCallbacks
def CreateDataVaultFile(datavault, DataName, DependentVariablesList, IndependentVaraiblesList):
    file = yield datavault.new(DataName, DependentVariablesList, IndependentVaraiblesList)
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
        for key, value in parameterdict.iteritems():
            yield datavault.add_parameter(key, parameterdict[key])
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

'''
grab screenshot of the window and save the screenshot to sessionfolder
'''
def saveDataToSessionFolder(winId, SessionFolder, ScreenshotName):
    try:
        p = QtGui.QPixmap.grabWindow(winId)
        a = p.save(SessionFolder + '\\' + ScreenshotName + '.jpg','jpg')
        if not a:
            print("Error saving Scan data picture")
    except Exception as inst:
        print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)
    
    def AutoSetLevels(self):
        ZeroRemoved = self.ImageData[self.ImageData != 0.0]
        Min, Max = np.amin(ZeroRemoved), np.amax(ZeroRemoved)
        if Min == Max:
            Min = Max - 10**-15
        pg.ImageView.setLevels(self, Min, Max)

    def AutoSetRange(self, data, pos, scale): #
        pg.ImageView.setImage(self, data, autoLevels = False, pos = pos, scale = scale)

