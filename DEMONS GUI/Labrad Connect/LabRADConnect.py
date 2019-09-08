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
        'SR830'   : False,
        'SR860'   : False,
        'SIM900'   : False,
        'GPIBDeviceManager'   : False,
        'GPIBServer'   : False,
        'AMI430'   : False,
        'IPS120'   : False,
        }
        self.LabradDictionary['4KMonitor'] = {
        'cxn': False,
        'IPS120': False,
        }
        
        self.pushButtonDictionary = {}
        self.pushButtonDictionary['Local'] = {
        'cxn'       : self.pushButton_LabRAD,
        'dv'        : self.pushButton_DataVault,
        'ser_server': self.pushButton_SerialServer,
        'DACADC'   : self.pushButton_DACADC,
        'SR830'   : self.pushButton_SR830,
        'SR860'   : self.pushButton_SR860,
        'SIM900'   : self.pushButton_SIM900,
        'GPIBDeviceManager'   : self.pushButton_GPIBDeviceManager,
        'GPIBServer'   : self.pushButton_GPIBServer,
        'AMI430'   : self.pushButton_AMI430,
        'IPS120'   : self.pushButton_IPS120,
        }
        self.pushButtonDictionary['4KMonitor'] = {
        'cxn': self.pushButton_4KMonitor_LabRAD,
        'IPS120': self.pushButton_4KMonitor_IPS120,
        }

        self.labelDictionary = {}
        self.labelDictionary['Local'] = {
        'cxn'       : self.label_Labrad,
        'dv'        : self.label_DataVault,
        'ser_server': self.label_SerialServer,
        'DACADC'   : self.label_DACADC,
        'SR830'   : self.label_SR830,
        'SR860'   : self.label_SR860,
        'SIM900'   : self.label_SIM900,
        'GPIBDeviceManager'   : self.label_GPIBDeviceManager,
        'GPIBServer'   : self.label_GPIBServer,
        'AMI430'   : self.label_AMI430,
        'IPS120'   : self.label_IPS120,
        }
        self.labelDictionary['4KMonitor'] = {
        'cxn': self.label_4KMonitor_Labrad,
        'IPS120': self.label_4KMonitor_IPS120,
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
        self.pushButton_SR860.clicked.connect(lambda: self.connectServer('Local', 'SR860'))
        self.pushButton_SIM900.clicked.connect(lambda: self.connectServer('Local', 'SIM900'))
        self.pushButton_GPIBDeviceManager.clicked.connect(lambda: self.connectServer('Local', 'GPIBDeviceManager'))
        self.pushButton_GPIBServer.clicked.connect(lambda: self.connectServer('Local', 'GPIBServer'))
        self.pushButton_AMI430.clicked.connect(lambda: self.connectServer('Local', 'AMI430'))
        self.pushButton_IPS120.clicked.connect(lambda: self.connectServer('Local', 'IPS120'))

        self.pushButton_4KMonitor_ConnectAll.clicked.connect(lambda: self.connectAllServers('4KMonitor'))
        self.pushButton_4KMonitor_DisconnectAll.clicked.connect(lambda: self.disconnectAllServers('4KMonitor'))

        self.pushButton_4KMonitor_LabRAD.clicked.connect(lambda: self.connectServer('4KMonitor', 'cxn'))
        self.pushButton_4KMonitor_IPS120.clicked.connect(lambda: self.connectServer('4KMonitor', 'IPS120'))
        
        self.pushButton_DataVaultFolder.clicked.connect(self.chooseDVFolder)
        self.pushButton_SessionFolder.clicked.connect(self.chooseSessionFolder)
    
    def setupAdditionalUi(self):
        pass

    @inlineCallbacks
    def connectServer(self, LabradPosition, servername, disconnect = True): #Click to toggle connection to a server
        try:
            if self.LabradDictionary[LabradPosition][servername] is False:
                if servername == 'cxn':
                    from labrad.wrappers import connectAsync
                    try:
                        if LabradPosition == 'Local':
                            cxn = yield connectAsync(host = '127.0.0.1', password = LABRADPASSWORD)
                        elif LabradPosition == '4KMonitor':
                            cxn = yield connectAsync(host = '4KMonitor', password = LABRADPASSWORD)
                        self.LabradDictionary[LabradPosition][servername] = cxn
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' Labrad failed, Error: ', inst)
                elif servername == 'dv':
                    try:
                        dv = yield self.LabradDictionary[LabradPosition]['cxn'].data_vault
                        self.LabradDictionary[LabradPosition][servername] = dv

                        if LabradPosition == 'Local':
                            reg = self.LabradDictionary[LabradPosition]['cxn'].registry #Set Registry
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
                        ser_server = yield self.LabradDictionary[LabradPosition]['cxn'].servers[serialServerName]
                        self.LabradDictionary[LabradPosition][servername] = ser_server
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' Serial Server failed, Error: ', inst)
                elif servername == 'DACADC':
                    try:
                        dac = yield self.LabradDictionary[LabradPosition]['cxn'].dac_adc
                        self.LabradDictionary[LabradPosition][servername] = dac
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' DAC_ADC Server failed, Error: ', inst)
                elif servername == 'SR830':
                    try:
                        sr830 = yield self.LabradDictionary[LabradPosition]['cxn'].sr830
                        self.LabradDictionary[LabradPosition][servername] = sr830
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' SR830 Server failed, Error: ', inst)
                elif servername == 'SR860':
                    try:
                        sr860 = yield self.LabradDictionary[LabradPosition]['cxn'].sr860
                        self.LabradDictionary[LabradPosition][servername] = sr860
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' SR860 Server failed, Error: ', inst)
                elif servername == 'SIM900':
                    try:
                        sim900 = yield self.LabradDictionary[LabradPosition]['cxn'].sim900
                        self.LabradDictionary[LabradPosition][servername] = sim900
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' SIM900 Server failed, Error: ', inst)
                elif servername == 'GPIBDeviceManager':
                    try:
                        gpib_device_manager = yield self.LabradDictionary[LabradPosition]['cxn'].gpib_device_manager
                        self.LabradDictionary[LabradPosition][servername] = gpib_device_manager
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' GPIB Device Server failed, Error: ', inst)
                elif servername == 'GPIBServer':
                    try:
                        computerName = platform.node() # get computer name
                        gpibServerName = computerName.lower().replace(' ','_').replace('-','_') + '_gpib_bus'
                        gpib_server = yield self.LabradDictionary[LabradPosition]['cxn'].servers[gpibServerName]
                        self.LabradDictionary[LabradPosition][servername] = gpib_server
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' GPIB Server failed, Error: ', inst)
                elif servername == 'AMI430':
                    try:
                        ami430 = yield self.LabradDictionary[LabradPosition]['cxn'].ami_430
                        self.LabradDictionary[LabradPosition][servername] = ami430
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' AMI430 Server failed, Error: ', inst)
                elif servername == 'IPS120':
                    try:
                        ips = yield self.LabradDictionary[LabradPosition]['cxn'].ips120_power_supply
                        self.LabradDictionary[LabradPosition][servername] = ips
                        connection_flag = True
                    except Exception as inst:
                        connection_flag = False
                        print('Connect to ', LabradPosition, ' IPS120 Server failed, Error: ', inst)

                if connection_flag:
                    if LabradPosition == 'Local':
                        Prefix = ''
                    else:
                        Prefix = LabradPosition + ' '
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
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)
            
    def disconnectServer(self, LabradPosition, servername): 
        try:
            self.LabradDictionary[LabradPosition][servername] = False
            self.labelDictionary[LabradPosition][servername].setText('Disconnected.')
            self.pushButtonDictionary[LabradPosition][servername].setStyleSheet('#' + str(self.pushButtonDictionary[LabradPosition][servername].objectName()) + '{background: rgb(161, 0, 0);border-radius: 4px;}')
            if LabradPosition == 'Local':
                Prefix = ''
            else:
                Prefix = LabradPosition + ' '
            self.discxnsignal.emit(Prefix + servername)
        except Exception as inst:
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)
    
    @inlineCallbacks
    def connectAllServers(self, LabradPosition):
        yield self.connectServer(LabradPosition, 'cxn', False)
        yield self.sleep(1)
        for name in self.LabradDictionary[LabradPosition]:
            if name == 'cxn':
                pass
            else:
                yield self.connectServer(LabradPosition, name, False)
            
    def disconnectAllServers(self, LabradPosition):
        for name in self.LabradDictionary[LabradPosition]:
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
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)
   
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
            print('Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno)

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
