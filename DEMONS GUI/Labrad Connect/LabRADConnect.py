from PyQt5 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import twisted
import numpy as np
import pyqtgraph as pg
#import exceptions
import time
import sys
import platform
import datetime
import os
import dirExplorer

LABRADPASSWORD = 'sSET2018'
NUMBER_CXNS = 3
path = os.path.dirname(os.path.realpath(__file__))
LabRADConnectUI, QtBaseClass = uic.loadUiType(os.path.join(path, "LabRADConnect.ui"))

class Window(QtGui.QMainWindow, LabRADConnectUI):
    cxnsignal = QtCore.pyqtSignal(str, object)
    discxnsignal = QtCore.pyqtSignal(str)
    newSessionFolder = QtCore.pyqtSignal(str)
    newDVFolder = QtCore.pyqtSignal(list)
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        self.moveDefault()
        
        #Initialize variables for all possible server connections in a dictionary
        #Makes multiple connections for browsing data vault in every desired context
        self.LabradDictionary = {}
        self.LabradDictionary['Local'] = {
        'cxn'       : False,
        'dv'        : False,
        'ser_server': False,
        'DACADC'   : False,
        'SR830_0'   : False,
        'SR830_1'   : False,
        'Lakeshore'   : False,
        'GPIBDeviceManager'   : False,
        'GPIBServer'   : False,
        'AMI430_X'   : False,
        'AMI430_Y'   : False,
        'AMI430_Z'   : False,
        'Keithley2450': False,
        'Levelmeter': False,
        }
        
        self.pushButtonDictionary = {}
        self.pushButtonDictionary['Local'] = {
        'cxn'       : self.pushButton_LabRAD,
        'dv'        : self.pushButton_DataVault,
        'ser_server': self.pushButton_SerialServer,
        'DACADC'   : self.pushButton_DACADC,
        'SR830'   : self.pushButton_SR830,
        'Lakeshore'   : self.pushButton_Lakeshore,
        'GPIBDeviceManager'   : self.pushButton_GPIBDeviceManager,
        'GPIBServer'   : self.pushButton_GPIBServer,
        'AMI430'   : self.pushButton_AMI430,
        'Keithley2450': self.pushButton_Keithley2450,
        'Levelmeter': self.pushButton_Levelmeter,
        }

        self.labelDictionary = {}
        self.labelDictionary['Local'] = {
        'cxn'       : self.label_Labrad,
        'dv'        : self.label_DataVault,
        'ser_server': self.label_SerialServer,
        'DACADC'   : self.label_DACADC,
        'SR830'   : self.label_SR830,
        'Lakeshore'   : self.label_Lakeshore,
        'GPIBDeviceManager'   : self.label_GPIBDeviceManager,
        'GPIBServer'   : self.label_GPIBServer,
        'AMI430'   : self.label_AMI430,
        'Keithley2450': self.label_Keithley2450,
        'Levelmeter': self.label_Levelmeter,
        }

        #Data vault session info
        self.lineEdit_DataVaultFolder.setReadOnly(True)
        self.DVFolder = ''
        self.lineEdit_DataVaultFolder.setText(self.DVFolder)
        
        #Saving images of all data taken info
        self.lineEdit_SessionFolder.setReadOnly(True)
        self.SessionFolder = ''
        self.lineEdit_SessionFolder.setText(self.SessionFolder)
        
        self.pushButton_ConnectAll.clicked.connect(lambda: self.connectAllServers('Local'))
        self.pushButton_DisconnectAll.clicked.connect(lambda: self.disconnectAllServers('Local'))

        self.pushButton_LabRAD.clicked.connect(lambda: self.connectServer('Local', 'cxn'))
        self.pushButton_DataVault.clicked.connect(lambda: self.connectServer('Local', 'dv'))
        self.pushButton_DACADC.clicked.connect(lambda: self.connectServer('Local', 'DACADC'))
        self.pushButton_SerialServer.clicked.connect(lambda: self.connectServer('Local', 'ser_server'))
        self.pushButton_SR830.clicked.connect(lambda: self.connectServer('Local', 'SR830'))
        self.pushButton_Lakeshore.clicked.connect(lambda: self.connectServer('Local', 'Lakeshore'))
        self.pushButton_GPIBDeviceManager.clicked.connect(lambda: self.connectServer('Local', 'GPIBDeviceManager'))
        self.pushButton_GPIBServer.clicked.connect(lambda: self.connectServer('Local', 'GPIBServer'))
        self.pushButton_AMI430.clicked.connect(lambda: self.connectServer('Local', 'AMI430'))
        self.pushButton_Keithley2450.clicked.connect(lambda: self.connectServer('Local','Keithley2450'))
        self.pushButton_Levelmeter.clicked.connect(lambda: self.connectServer('Local','Levelmeter'))
        self.pushButton_DataVaultFolder.clicked.connect(self.chooseDVFolder)
        self.pushButton_SessionFolder.clicked.connect(self.chooseSessionFolder)
    
    def setupAdditionalUi(self):
        pass

    @inlineCallbacks
    def connectServer(self, LabradPosition, servername, disconnect = True): #Click to toggle connection to a server
        try:
            t = ''
            if servername == 'AMI430':
                t = servername + '_X'
            elif servername == 'SR830':
                t = servername + '_0'
            else:
                t = servername
            if self.LabradDictionary[LabradPosition][t] is False:
                if servername == 'cxn':
                    from labrad.wrappers import connectAsync
                    try:
                        self.LabradDictionary[LabradPosition][servername] = [False]*NUMBER_CXNS
                        for j in range(0,NUMBER_CXNS):
                            if LabradPosition == 'Local':
                                cxn = yield connectAsync(host = '127.0.0.1', password = LABRADPASSWORD)
                            #elif LabradPosition == '4KMonitor':
                                #cxn = yield connectAsync(host = '4KMonitor', password = LABRADPASSWORD)
                            self.LabradDictionary[LabradPosition][servername][j] = cxn
                        print(self.LabradDictionary)
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' Labrad failed, Error: ', inst)
                elif servername == 'dv':
                    try:
                        dv = yield self.LabradDictionary[LabradPosition]['cxn'][0].data_vault
                        self.LabradDictionary[LabradPosition][servername] = dv

                        if LabradPosition == 'Local':
                            reg = self.LabradDictionary[LabradPosition]['cxn'][0].registry #Set Registry
                            yield reg.cd('')#Back to root directory
                            yield reg.cd(['Servers', 'Data Vault', 'Repository']) #Go into Repository
                            settinglist = yield reg.dir() # read the default settings
                            self.osDVFolder = yield reg.get(settinglist[1][-1]) #Get the path from default settings
                            self.osDVFolder = self.osDVFolder.replace('/', '\\') #Transform into os format

                            self.DVFolder = self.osDVFolder
                            self.lineEdit_DataVaultFolder.setText(self.DVFolder)
                            self.newDVFolder.emit([])#Emit DataVault Default
                            connection_flag = True

                            self.SessionFolder = self.osDVFolder + '\\Image' + '\\' + str(datetime.date.today())
                            self.lineEdit_SessionFolder.setText(self.SessionFolder)
                            self.newSessionFolder.emit(self.SessionFolder)

                            folderExists = os.path.exists(self.SessionFolder)
                            if not folderExists:
                                os.makedirs(self.SessionFolder)
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' Data Vault failed, Error: ', inst)
                elif servername == 'ser_server':
                    try:
                        computerName = platform.node() # get computer name
                        serialServerName = computerName.lower().replace(' ','_').replace('-','_') + '_serial_server'
                        ser_server = yield self.LabradDictionary[LabradPosition]['cxn'][0].servers[serialServerName]
                        self.LabradDictionary[LabradPosition][servername] = ser_server
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' Serial Server failed, Error: ', inst)
                elif servername == 'DACADC':
                    try:
                        dac = yield self.LabradDictionary[LabradPosition]['cxn'][0].dac_adc_24bits
                        self.LabradDictionary[LabradPosition][servername] = dac
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' DAC_ADC Server failed, Error: ', inst)
                elif servername == 'SR830':
                    try:
                        for i in range(0,2):
                            sr830 = yield self.LabradDictionary[LabradPosition]['cxn'][i].sr830
                            sname = servername + '_' + str(i)
                            self.LabradDictionary[LabradPosition][sname] = sr830
                            self.cxnsignal.emit(sname, self.LabradDictionary[LabradPosition][sname])

                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' SR830 Server failed, Error: ', inst)
                elif servername == 'Lakeshore':
                    try:
                        lsci_model350 = yield self.LabradDictionary[LabradPosition]['cxn'][0].lsci_model350
                        self.LabradDictionary[LabradPosition][servername] = lsci_model350
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' Lakeshore Server failed, Error: ', inst)
                elif servername == 'GPIBDeviceManager':
                    try:
                        gpib_device_manager = yield self.LabradDictionary[LabradPosition]['cxn'][0].gpib_device_manager
                        self.LabradDictionary[LabradPosition][servername] = gpib_device_manager
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' GPIB Device Server failed, Error: ', inst)
                elif servername == 'GPIBServer':
                    try:
                        computerName = platform.node() # get computer name
                        gpibServerName = computerName.lower().replace(' ','_').replace('-','_') + '_gpib_bus'
                        gpib_server = yield self.LabradDictionary[LabradPosition]['cxn'][0].servers[gpibServerName]
                        self.LabradDictionary[LabradPosition][servername] = gpib_server
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' GPIB Server failed, Error: ', inst)
                elif servername == 'AMI430':
                    try:
                        suffix_list = ['X','Y','Z']
                        for i in range(0,3):
                            ami430 = yield self.LabradDictionary[LabradPosition]['cxn'][i].ami_430
                            sname = servername + '_' + suffix_list[i] 
                            self.LabradDictionary[LabradPosition][sname] = ami430
                            self.cxnsignal.emit(sname, self.LabradDictionary[LabradPosition][sname])
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' AMI430 Server failed, Error: ', inst)

                elif servername == 'Keithley2450':
                    try:
                        keithley_2450 = yield self.LabradDictionary[LabradPosition]['cxn'][0].keithley_2450
                        self.LabradDictionary[LabradPosition][servername] = keithley_2450
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' Keithley2450 Server failed, Error: ', inst)
                
                elif servername == 'Levelmeter':
                    try:
                        levelmeter = yield self.LabradDictionary[LabradPosition]['cxn'][0].helium_level_meter
                        self.LabradDictionary[LabradPosition][servername] = levelmeter
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' Keithley2450 Server failed, Error: ', inst)

                if connection_flag:
                    if LabradPosition == 'Local':
                        Prefix = ''
                    else:
                        Prefix = LabradPosition + ' '
                    if servername != 'AMI430' and servername != 'SR830':
                        self.cxnsignal.emit(Prefix + servername, self.LabradDictionary[LabradPosition][servername])
                    self.labelDictionary[LabradPosition][servername].setText('Connected')
                    self.pushButtonDictionary[LabradPosition][servername].setStyleSheet('#' + str(self.pushButtonDictionary[LabradPosition][servername].objectName()) + '{background: rgb(0, 170, 0);border-radius: 4px;}')
                else:
                    self.labelDictionary[LabradPosition][servername].setText('Connection Failed.')
                    self.pushButtonDictionary[LabradPosition][servername].setStyleSheet('#' + str(self.pushButtonDictionary[LabradPosition][servername].objectName()) + '{background: rgb(161, 0, 0);border-radius: 4px;}')
            else:
                if disconnect:
                    self.disconnectServer(LabradPosition, servername)
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
            
    def disconnectServer(self, LabradPosition, servername): 
        try:
            suffix = ['X','Y','Z']
            if servername == 'AMI430':
                for k in range(0,3):
                    sname = servername + '_' + suffix[k]
                    self.LabradDictionary[LabradPosition][sname] = False
                    self.discxnsignal.emit(sname)
            elif servername == 'SR830':
                for k in range(0,2):
                    sname = servername + '_' + str(k)
                    self.LabradDictionary[LabradPosition][sname] = False
                    self.discxnsignal.emit(sname)
            else:
                self.LabradDictionary[LabradPosition][servername] = False
            self.labelDictionary[LabradPosition][servername].setText('Disconnected.')
            self.pushButtonDictionary[LabradPosition][servername].setStyleSheet('#' + str(self.pushButtonDictionary[LabradPosition][servername].objectName()) + '{background: rgb(161, 0, 0);border-radius: 4px;}')
            if LabradPosition == 'Local':
                Prefix = ''
            else:
                Prefix = LabradPosition + ' '
            self.discxnsignal.emit(Prefix + servername)
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
    
    @inlineCallbacks
    def connectAllServers(self, LabradPosition):
        yield self.connectServer(LabradPosition, 'cxn', False)
        yield self.sleep(1)
        for name in self.pushButtonDictionary[LabradPosition]:
            if name == 'cxn':
                pass
            else:
                yield self.connectServer(LabradPosition, name, False)
        print(self.LabradDictionary)
            
    def disconnectAllServers(self, LabradPosition):
        for name in self.pushButtonDictionary[LabradPosition]:
            self.disconnectServer(LabradPosition, name)

    @inlineCallbacks
    def chooseDVFolder(self, c = None):
        try:
            if self.LabradDictionary['Local']['dv'] is False:
                msgBox = QtGui.QMessageBox(self)
                msgBox.setIcon(QtGui.QMessageBox.Information)
                msgBox.setWindowTitle('Data Vault Connection Missing')
                msgBox.setText("\r\n Cannot choose data vault folder until connected to data vault.")
                msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
                msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                msgBox.exec_()
            else: 
                dv = self.LabradDictionary['Local']['dv']
                dvExplorer = dirExplorer.dataVaultExplorer(dv, self.reactor, self)
                yield dvExplorer.popDirs()
                dvExplorer.show()
                dvExplorer.raise_()
                dvExplorer.accepted.connect(lambda: self.OpenDataVaultFolder(self.reactor, dv, dvExplorer.directory)) 

        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)
   
    @inlineCallbacks
    def OpenDataVaultFolder(self, c, datavault, directory):
        try:
            yield datavault.cd(directory)
            directory = directory[1:]
            DVFolder, osDVFolder = '', ''
            DVList = []
            for i in directory:
                DVList.append(i)
                DVFolder = DVFolder + '\\' + i
                osDVFolder = osDVFolder +'\\' + i + '.dir'
            self.DVFolder =  self.osDVFolder + '\\' + DVFolder
            self.SessionFolder = self.osDVFolder + '\\' + osDVFolder + '\\Image' + '\\' + str(datetime.date.today())
            self.lineEdit_DataVaultFolder.setText(self.DVFolder)
            self.lineEdit_SessionFolder.setText(self.SessionFolder)
            self.newDVFolder.emit(DVList)
            self.newSessionFolder.emit(self.SessionFolder)

            folderExists = os.path.exists(self.SessionFolder)
            if not folderExists:
                os.makedirs(self.SessionFolder)
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_info()[2].tb_lineno)

    def chooseSessionFolder(self):
        folder = str(QtGui.QFileDialog.getExistingDirectory(self, self.SessionFolder))
        if folder:
            self.SessionFolder = folder
            self.lineEdit_SessionFolder.setText(self.SessionFolder)
            self.newSessionFolder.emit(self.SessionFolder)
        
    def moveDefault(self):    
        self.move(650, 10)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
