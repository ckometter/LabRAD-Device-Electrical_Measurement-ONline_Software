import numpy as np
from PyQt5 import QtCore, QtGui
import pyqtgraph as pg


app = QtGui.QApplication([])

## Create window with two ImageView widgets
win = QtGui.QMainWindow()
win.resize(800,800)
cw = QtGui.QWidget()
win.setCentralWidget(cw)
l = QtGui.QGridLayout()
cw.setLayout(l)
imv1 = pg.ImageView()
imv2 = pg.PlotWidget()
l.addWidget(imv1, 0, 0)
l.addWidget(imv2, 1, 0)
win.show()

#roi = pg.LineSegmentROI([[[0, 0], [10,0]]], pen='r')
roi = pg.ROI([0,0],pen='r',snapSize=1.0)
roi.addTranslateHandle((0,0),(0,0))
roi.addScaleHandle((1,1),(0,0))
imv1.addItem(roi)

x1 = np.linspace(-30, 10, 128)[:, np.newaxis, np.newaxis]
x2 = np.linspace(-20, 20, 128)[:, np.newaxis, np.newaxis]
y = np.linspace(-30, 10, 128)[np.newaxis, :, np.newaxis]
z = np.linspace(-20, 20, 128)[np.newaxis, np.newaxis, :]
d1 = np.sqrt(x1**2 + y**2 + z**2)
d2 = 2*np.sqrt(x1[::-1]**2 + y**2 + z**2)
d3 = 4*np.sqrt(x2**2 + y[:,::-1]**2 + z**2)
#data = (np.sin(d1) / d1**2) + (np.sin(d2) / d2**2) + (np.sin(d3) / d3**2)
data = np.array([np.linspace(0,20,5),np.linspace(0,20,5),np.linspace(0,20,5)])
print(data)
def update():
    global data, imv1, imv2
    imv2.clear()
    d2,f = roi.getArrayRegion(data, imv1.imageItem,returnMappedCoords=True,axes=(0,1))
    
    print('d2')
    print(d2)
    d2 = np.mean(d2,axis = 0)
    print(d2)
    print('f')
    print(f)
    print(f[0])
    print(f[1])
    #d2 = roi.getArrayRegion(data, imv1.imageItem, axes=(0,1))
    imv2.plot(f[1,0,:],d2)
    
roi.sigRegionChanged.connect(update)


## Display the data
imv1.setImage(data,pos=[0,0],scale=[1,1])
imv1.setHistogramRange(0, 20)
imv1.setLevels(0,20)

update()

## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
