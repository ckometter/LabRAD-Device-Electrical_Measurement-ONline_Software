from __future__ import division
import sys
import os
import twisted
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
from PyQt5 import Qt, QtGui, QtCore, uic
import numpy as np
#import exceptions
import time
import threading
import copy
from scipy.signal import detrend
import dirExplorer
#importing a bunch of stuff


path = os.path.dirname(os.path.realpath(__file__))
ControlerWindowUI, QtBaseClass = uic.loadUiType(os.path.join(path, "DVPlotterWindow.ui"))

#Not required, but strongly recommended functions used to format numbers in a particular way.
#sys.path.append(sys.path[0]+'\Resources')
from DEMONSFormat import *

ID_NEWDATA = 999


class Window(QtGui.QMainWindow, ControlerWindowUI):

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)
        self.dv = False
        self.localcxn = False
        self.dvfolder = False
        self.osDVFolder = False
        self.fileselectbool = False
        self.importedbool = False
        self.refreshing = False
        self.id = ID_NEWDATA

        self.signaldictionary = {}

        self.plotobject = None
        self.ROIObject = pg.ROI([0,0],pen='r',translateSnap=True,scaleSnap=True,snapSize=0.5)
        self.ROIObject.addTranslateHandle((0,0),(0,0))
        self.ROIObject.addScaleHandle((1,1),(0,0))

        #self.pushButton_Servers.clicked.connect(self.showServersList)

        self.serversList = { #Dictionary including toplevel server received from labrad connect
        }

        self.DeviceList = {}#self.DeviceList['Device Name'][Device Property]

        self.Plotlist = {}

        self.raw_data = []
        self.dep_variables = []
        self.indep_variables = []
        self.parameters = {}
        self.parameters['CustomVar'] = ''


        self.lineEdits = {
            'CustomVar': self.lineEdit_Custom,
        }
        self.DetermineEnableConditions()
        self.Refreshinterface()
        self.pushButton_ConnectDV.clicked.connect(lambda: createDVClient(self, self.localcxn))
        self.pushButton_DVFile.clicked.connect(self.chooseDVFile)    
        self.pushButton_ImportData.clicked.connect(lambda: self.importDVData(self.dv))
    
        self.pushButton_Plot1D.clicked.connect(lambda: self.Plot1DData())
        self.pushButton_plotRefresh.clicked.connect(self.PlotRefreshWrapper)
        self.pushButton_Plot2D.clicked.connect(lambda: self.Plot2DData())
        self.lineEdit_Custom.editingFinished.connect(lambda: UpdateLineEdit_String(self.parameters,'CustomVar',self.lineEdits))

        self.pushButton_AddROIPlot.clicked.connect(lambda: addROIPlot(self.Plotlist,self.ROIObject,self.comboBox_1DCut,self.label_1DCut))
        self.pushButton_Close1D.clicked.connect(lambda: closeROIPlot(self.Plotlist,self.ROIObject))
        self.pushButton_Save2D.clicked.connect(lambda: save2DPlot(self,self.Plotlist))
        self.pushButton_SaveWindow.clicked.connect(lambda: saveWindow(self))
        #if '2DPlot' in self.Plotlist:
        #    if self.Plotlist['2DPlot']['ROI'] is not None:
        #        self.Plotlist['2DPlot']['ROI'].sigRegionChanged.connect(lambda: updateROIPlot(self.Plotlist))


    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.pushButton_DVFile: not (self.dv==False) and not self.refreshing,
            self.pushButton_ImportData: not (self.fileselectbool == False) and not self.refreshing,
            self.pushButton_plotRefresh: ('1DPlot' in self.Plotlist or '2DPlot' in self.Plotlist),
            self.pushButton_ConnectDV: True,
            self.comboBox_indepx: not self.refreshing,
            self.comboBox_indepy: not self.refreshing,
            self.comboBox_dep: not self.refreshing,
            self.lineEdit_Custom: not self.refreshing,
        }


    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)
        if self.dv == False:
            setIndicator(self.pushButton_DVBool, 'rgb(161,0,0)')
        else:
            setIndicator(self.pushButton_DVBool, 'rgb(0,170,0)')
        if self.fileselectbool == False:
            setIndicator(self.pushButton_FileBool, 'rgb(161,0,0)')
        else:
            setIndicator(self.pushButton_FileBool,'rgb(0,170,0)')
        if self.importedbool == False:
            setIndicator(self.pushButton_ImportBool, 'rgb(161,0,0)')
        else:
            setIndicator(self.pushButton_ImportBool,'rgb(0,170,0)')
        ReconstructComboBox(self.comboBox_indepx,self.indep_variables)
        ReconstructComboBox(self.comboBox_indepy,self.indep_variables)
        ReconstructComboBox(self.comboBox_dep,self.dep_variables)
        
    @inlineCallbacks
    def chooseDVFile(self, c=None):
        try:
            dv = self.dv
            dvExplorer = dirExplorer.dataVaultExplorer(dv,self.reactor,parent=self)
            yield dvExplorer.popDirs()
            dvExplorer.show()
            dvExplorer.raise_()
            dvExplorer.accepted.connect(lambda: self.OpenDataVaultFile(self.reactor, dv, dvExplorer.directory,dvExplorer.selectedfile))
        except Exception as inst:
            print('Error:',inst, 'on line: ', sys.exc_info()[2].tb_lineno) 

    @inlineCallbacks
    def OpenDataVaultFile(self,c,datavault,directory,filelist):
        yield datavault.cd(directory)
        yield datavault.open(filelist)
        self.label_DVFile.setText(filelist)
        if len(filelist) > 1:
            self.fileselectbool = True
        else:
            self.fileselectbool = False
        dvfolderstring = ''
        for i in directory[1:]:
            dvfolderstring = dvfolderstring + '\\' + i
        newfolder = str(self.osDVFolder + dvfolderstring)
        self.dvfolder = newfolder
        self.label_DVFolder.setText(newfolder)
        self.importedbool = False
        self.Refreshinterface()
    
    @inlineCallbacks
    def importDVData(self,dv,c=None):
        self.id += 1
        commentstruct = yield dv.get_comments()
        name = yield dv.get_name()
        parameterstruct = yield dv.get_parameters()
        totalstring = ''
        self.textBrowser_Comments.setText('')
        totalstring += 'Filename: '+str(name) + '\n'
        totalstring += 'Comments: ' + '\n'
        if commentstruct is not None:
            for i in commentstruct:
                totalstring += i[2] + '\n'
        if parameterstruct is not None:
            totalstring += 'Parameters: ' + '\n'
            for j in parameterstruct:
                totalstring += str(j[0]) + ': ' + str(j[1]) + '\n'
        totalstring += '\n'
        totalstring += 'Import Time: ' + time.asctime(time.localtime(time.time())) + '\n'
        self.textBrowser_Comments.setText(totalstring)
        variablestruct = yield dv.variables()
        #clear formerly stored variables
        self.indep_variables = []
        self.dep_variables = []
        for el in variablestruct[0]:
            self.indep_variables.append(str(el[0]))
        for el in variablestruct[1]:
            self.dep_variables.append(str(el[0]))
        self.dep_variables.append("Custom")

        # Reads in data in chunks of size chunk_num rows - not 
        # self.raw_data = [[]]
        # chunk_num = 1
        # read_loop = True
        # while read_loop:
        #     dataset = yield dv.get(chunk_num)
        #     if len(dataset) < chunk_num:
        #         read_loop = False
        #     self.raw_data = np.append(self.raw_data, dataset)
        self.raw_data = yield dv.get(10000,True)
        self.raw_data = np.array(self.raw_data)
        self.importedbool = True
        self.Refreshinterface()

    def moveDefault(self):
        self.move(10,170)
        
    @inlineCallbacks
    def Plot1DData(self):
        ClearPlots(self.Plotlist)
        self.ROIObject = pg.ROI([0,0],pen='r',translateSnap=True,scaleSnap=True,snapSize=0.5)
        self.ROIObject.addTranslateHandle((0,0),(0,0))
        self.ROIObject.addScaleHandle((1,1),(0,0))


        self.Plotlist = {}
        self.plotobject = pg.PlotWidget(parent=None)
        self.Plotlist['1DPlot'] = {
            'PlotObject': self.plotobject,
            'PlotData': [[],[]],
            'Layout': self.Layout_Plot,
            'Title': None,
            'XAxisName': None,
            'XUnit': None,
            'YAxisName': None,
            'YUnit': None,
            'xvarloc': None,
            'yvarloc': None,
            'yvar': None,
            'ROI': None,
            'ROIPlot': None
        }

        xvar = self.comboBox_indepx.currentText()
        yvar = self.comboBox_dep.currentText()
        yunit = self.lineEdit_unitdep.text()
        xunit = self.lineEdit_unitindepx.text()

        if yvar == 'Custom':
            ylabel = self.parameters['CustomVar']
        else:
            ylabel = yvar
        Setup1DPlot(self.Plotlist['1DPlot']['PlotObject'],self.Plotlist['1DPlot']['Layout'], str(xvar + " vs. " + ylabel), ylabel, yunit, xvar, xunit)
        #self.importDVData(self.dv)

        filename = self.label_DVFile.text()
        if filename not in self.signaldictionary:
            self.signaldictionary[filename] = self.id
            yield self.dv.signal__data_available(self.id)

        xvar_loc = self.indep_variables.index(xvar)
        yvar_loc = len(self.indep_variables) + self.dep_variables.index(yvar)
        xdata = self.raw_data[:,xvar_loc]
        ydata = []

        if yvar == 'Custom':
            variable_list = self.dep_variables
            operator_list = ['^','*','/','+','-','(',')']
            array = self.raw_data[:,len(self.indep_variables):]
            customstring = self.parameters['CustomVar']
            ydata = loopCustom(variable_list,operator_list,array,customstring)
        else:
            ydata = self.raw_data[:,yvar_loc]
        self.Plotlist['1DPlot']['PlotData'][0] = xdata
        self.Plotlist['1DPlot']['PlotData'][1] = ydata
        self.Plotlist['1DPlot']['xvarloc'] = xvar_loc
        self.Plotlist['1DPlot']['yvarloc'] = yvar_loc
        self.Plotlist['1DPlot']['yvar'] = yvar

        Plot1DData(self.Plotlist['1DPlot']['PlotData'][0], self.Plotlist['1DPlot']['PlotData'][1],self.Plotlist['1DPlot']['PlotObject'])
        self.Refreshinterface()

    @inlineCallbacks
    def Plot2DData(self):
        ClearPlots(self.Plotlist)
        self.ROIObject = pg.ROI([0,0],pen='r',translateSnap=True,scaleSnap=True,snapSize=0.5)
        self.ROIObject.addTranslateHandle((0,0),(0,0))
        self.ROIObject.addScaleHandle((1,1),(0,0))

        self.Plotlist = {}

        self.Plotlist['2DPlot'] = {
            'PlotObject': self.plotobject,
            'PlotData': [[],[],[]],
            'Layout': self.Layout_Plot,
            'Title': None,
            'XAxisName': None,
            'XUnit': None,
            'YAxisName': None,
            'YUnit': None,
            'ZAxisName':None,
            'ZUnit':None,
            'xvarloc': None,
            'yvarloc': None,
            'zvarloc': None,
            'Imageview':None,
            'zvar':None,
            'ROI': None,
            'ROIPlot': None,
            'Imagedata': None,
            'XAxisScale': None,
            'YAxisScale': None,
            'XPts': 0,
            'YPts': 0,
            'InterpType': 'Linear',

        }

        xvar = self.comboBox_indepx.currentText()
        yvar = self.comboBox_indepy.currentText()
        yunit = self.lineEdit_unitindepy.text()
        xunit = self.lineEdit_unitindepx.text()
        zunit = self.lineEdit_unitdep.text()
        zvar = self.comboBox_dep.currentText()

        self.Plotlist['2DPlot']['XPts'] = int(self.lineEdit_XPts.text())
        self.Plotlist['2DPlot']['YPts'] = int(self.lineEdit_YPts.text())
        self.Plotlist['2DPlot']['InterpType'] = self.comboBox_InterpType.currentText()

        ReconstructComboBox(self.comboBox_1DCut,[xvar,yvar])

        self.Plotlist['2DPlot']['PlotObject'] = Setup2DPlot(self.Plotlist['2DPlot']['Layout'],  yvar, yunit, xvar, xunit)
        self.Plotlist['2DPlot']['zvar'] = zvar
        filename = self.label_DVFile.text()
        if filename not in self.signaldictionary:
            self.signaldictionary[filename] = self.id
            yield self.dv.signal__data_available(self.id)

        xvar_loc = self.indep_variables.index(xvar)
        yvar_loc = self.indep_variables.index(yvar)
        zvar_loc = len(self.indep_variables) + self.dep_variables.index(zvar)

        if zvar == 'Custom':
            variable_list = self.dep_variables
            operator_list = ['^','*','/','+','-','(',')']
            array = self.raw_data[:,len(self.indep_variables):]
            customstring = self.parameters['CustomVar']
            zdata = loopCustom(variable_list,operator_list,array,customstring)
        else:
            zdata = self.raw_data[:,zvar_loc]

        xdata = self.raw_data[:,xvar_loc]
        ydata = self.raw_data[:,yvar_loc]
        self.Plotlist['2DPlot']['PlotData'][0] = xdata
        self.Plotlist['2DPlot']['PlotData'][1] = ydata
        self.Plotlist['2DPlot']['PlotData'][2] = zdata
        self.Plotlist['2DPlot']['xvarloc'] = xvar_loc
        self.Plotlist['2DPlot']['yvarloc'] = yvar_loc
        self.Plotlist['2DPlot']['zvarloc'] = zvar_loc
        self.Plotlist['2DPlot']['XAxisName'] = xvar
        self.Plotlist['2DPlot']['YAxisName'] = yvar
        if zvar == 'Custom':
            self.Plotlist['2DPlot']['Title'] = self.parameters['CustomVar']
        else:
            self.Plotlist['2DPlot']['Title'] = zvar
        self.Plotlist['2DPlot']['ZUnit'] = zunit
        self.Plotlist['2DPlot']['YUnit'] = yunit
        self.Plotlist['2DPlot']['XUnit'] = xunit
        img, minx, miny, scalex, scaley = CreateImage(self.Plotlist['2DPlot']['PlotData'][0],self.Plotlist['2DPlot']['PlotData'][1],self.Plotlist['2DPlot']['PlotData'][2],self.Plotlist['2DPlot']['XPts'],self.Plotlist['2DPlot']['YPts'],self.Plotlist['2DPlot']['InterpType'])
        self.Plotlist['2DPlot']['Imagedata'] = img
        self.Plotlist['2DPlot']['XAxisScale'] = scalex
        self.Plotlist['2DPlot']['YAxisScale'] = scaley
        self.Plotlist['2DPlot']['Minx'] = minx
        self.Plotlist['2DPlot']['Miny'] = miny

        Plot2DData(self.Plotlist['2DPlot']['PlotObject'],img, minx, miny, scalex,scaley,autoRange=True,autoLevels=True)
        self.Refreshinterface()

    def PlotRefreshWrapper(self):
        if self.refreshing == True:
            setIndicator(self.pushButton_plotRefresh, 'rgb(161,0,0)')
            self.PlotRefreshOff()
        else:
            setIndicator(self.pushButton_plotRefresh, 'rgb(0,161,0)')
            self.PlotRefreshOn()
        self.Refreshinterface()

    @inlineCallbacks
    def PlotRefreshOn(self):
        try:
            self.refreshing = True
            filename = self.label_DVFile.text()
            print(self.signaldictionary)
            yield self.dv.addListener(listener=self.updatePlot, ID=1000)
            #yield self.dv.addListener(listener=self.updatePlot, ID=self.signaldictionary[filename])
            interimdata = yield self.dv.get()
            if '1DPlot' in self.Plotlist:
                if len(np.array(interimdata)) > 0:
                    for line in interimdata:
                        self.raw_data = np.vstack([self.raw_data,line])
                        self.Plotlist['1DPlot']['PlotData'][0] = np.append(self.Plotlist['1DPlot']['PlotData'][0],line[self.Plotlist['1DPlot']['xvarloc']])
                        if self.Plotlist['1DPlot']['yvar'] == "Custom":
                            variable_list = self.dep_variables
                            operator_list = ['^','*','/','+','-','(',')']
                            array = [line[len(self.indep_variables):]]
                            customstring = self.parameters['CustomVar']
                            ydata = loopCustom(variable_list,operator_list,array,customstring)
                            self.Plotlist['1DPlot']['PlotData'][1] = np.append(self.Plotlist['1DPlot']['PlotData'][1],ydata)
                        else:
                            self.Plotlist['1DPlot']['PlotData'][1] = np.append(self.Plotlist['1DPlot']['PlotData'][1],line[self.Plotlist['1DPlot']['yvarloc']])
                    Plot1DData(self.Plotlist['1DPlot']['PlotData'][0], self.Plotlist['1DPlot']['PlotData'][1],self.Plotlist['1DPlot']['PlotObject'])
            
            if '2DPlot' in self.Plotlist:
                if len(np.array(interimdata)) > 0:
                    for line in interimdata:
                        self.raw_data = np.vstack([self.raw_data,line])
                        self.Plotlist['2DPlot']['PlotData'][0] = np.append(self.Plotlist['2DPlot']['PlotData'][0],line[self.Plotlist['2DPlot']['xvarloc']])
                        self.Plotlist['2DPlot']['PlotData'][1] = np.append(self.Plotlist['2DPlot']['PlotData'][1],line[self.Plotlist['2DPlot']['yvarloc']])
                        if self.Plotlist['2DPlot']['zvar'] == "Custom":
                            variable_list = self.dep_variables
                            operator_list = ['^','*','/','+','-','(',')']
                            array = [line[len(self.indep_variables):]]
                            customstring = self.parameters['CustomVar']
                            zdata = loopCustom(variable_list,operator_list,array,customstring)
                            self.Plotlist['2DPlot']['PlotData'][2] = np.append(self.Plotlist['2DPlot']['PlotData'][2],zdata)
                        else:
                            self.Plotlist['2DPlot']['PlotData'][2] = np.append(self.Plotlist['2DPlot']['PlotData'][2],line[self.Plotlist['2DPlot']['zzarloc']])
                    
                    img, minx, miny, scalex, scaley = CreateImage(self.Plotlist['2DPlot']['PlotData'][0],self.Plotlist['2DPlot']['PlotData'][1],self.Plotlist['2DPlot']['PlotData'][2],self.Plotlist['2DPlot']['XPts'],self.Plotlist['2DPlot']['YPts'],self.Plotlist['2DPlot']['InterpType'])
                    self.Plotlist['2DPlot']['Imagedata'] = img

                    if img != 0:
                        Plot2DData(self.Plotlist['2DPlot']['PlotObject'],img, minx, miny, scalex,scaley,autoRange=True,autoLevels=True)

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
            print("Error in PlotRefreshOn")

    @inlineCallbacks
    def PlotRefreshOff(self):
        try:
            self.refreshing = False
            filename = self.label_DVFile.text()
            yield self.dv.removeListener(listener=self.updatePlot, ID = self.signaldictionary[filename])

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
            print('error in PlotRefreshOff')

    @inlineCallbacks
    def updatePlot(self,c,signal):
        try:
            newData = yield self.dv.get()
            newData = np.array(newData)
            if '1DPlot' in self.Plotlist:
                for line in newData:
                    self.Plotlist['1DPlot']['PlotData'][0] = np.append(self.Plotlist['1DPlot']['PlotData'][0],line[self.Plotlist['1DPlot']['xvarloc']])
                    if self.Plotlist['1DPlot']['yvar'] == "Custom":
                        variable_list = self.dep_variables
                        operator_list = ['^','*','/','+','-','(',')']
                        array = [line[len(self.indep_variables):]]
                        customstring = self.parameters['CustomVar']
                        ydata = loopCustom(variable_list,operator_list,array,customstring)
                        self.Plotlist['1DPlot']['PlotData'][1] = np.append(self.Plotlist['1DPlot']['PlotData'][1],ydata)
                    else:
                        self.Plotlist['1DPlot']['PlotData'][1] = np.append(self.Plotlist['1DPlot']['PlotData'][1],line[self.Plotlist['1DPlot']['yvarloc']])
                Plot1DData(self.Plotlist['1DPlot']['PlotData'][0], self.Plotlist['1DPlot']['PlotData'][1],self.Plotlist['1DPlot']['PlotObject'])
        
            if '2DPlot' in self.Plotlist:
                for line in newData:
                    self.Plotlist['2DPlot']['PlotData'][0] = np.append(self.Plotlist['2DPlot']['PlotData'][0],line[self.Plotlist['2DPlot']['xvarloc']])
                    self.Plotlist['2DPlot']['PlotData'][1] = np.append(self.Plotlist['2DPlot']['PlotData'][1],line[self.Plotlist['2DPlot']['yvarloc']])
                    if self.Plotlist['2DPlot']['zvar'] == "Custom":
                        variable_list = self.dep_variables
                        operator_list = ['^','*','/','+','-','(',')']
                        array = [line[len(self.indep_variables):]]
                        customstring = self.parameters['CustomVar']
                        zdata = loopCustom(variable_list,operator_list,array,customstring)
                        self.Plotlist['2DPlot']['PlotData'][2] = np.append(self.Plotlist['2DPlot']['PlotData'][2],zdata)
                    else:
                        self.Plotlist['2DPlot']['PlotData'][2] = np.append(self.Plotlist['2DPlot']['PlotData'][2],line[self.Plotlist['2DPlot']['zvarloc']])
                
                img, minx, miny, scalex, scaley = CreateImage(self.Plotlist['2DPlot']['PlotData'][0],self.Plotlist['2DPlot']['PlotData'][1],self.Plotlist['2DPlot']['PlotData'][2],self.Plotlist['2DPlot']['XPts'],self.Plotlist['2DPlot']['YPts'],self.Plotlist['2DPlot']['InterpType'])
                self.Plotlist['2DPlot']['Imagedata'] = img

                Plot2DData(self.Plotlist['2DPlot']['PlotObject'],img, minx, miny, scalex,scaley,autoRange=True,autoLevels=True)
            yield SleepAsync(self.reactor, 3) #sleep 3 seconds 
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
            print('error in UpdatePlot')


