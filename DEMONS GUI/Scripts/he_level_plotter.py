import labrad
import numpy as np
import sys
import PyGnuplot as gp
import time

def main(*args):
    try:

        dv_file = int(sys.argv[1])
        cxn = labrad.connect()
        dv = cxn.data_vault
        dv.cd(['','he_level'])
        dv.open(dv_file)
        x,y = dv.get_ex_t()
        x = np.array(x)
        xp = np.zeros(len(x))
        y = np.array(y)
        for k in range(0,len(x)):
            structtime = time.localtime(x[k])
            xp[k] = structtime.tm_hour + float(structtime.tm_min)/60
        
        gp.s([xp,y])#,filename='"C:\\Users\\Feldman Lab\\code\\Setup_BF122019\\LabRAD-Device-Electrical_Measurement-ONline_Software-pyqt5\\DEMONS GUI\\Scripts\\tmp.dat"')
        title = time.strftime("%a, %d %b %Y",time.localtime(x[0]))
        time.sleep(2)
        gp.c('set terminal wxt size 500,500 position -1900,400 enhanced persist')
        gp.c('set title '+ '"' + title + '"')
        gp.c('set xlabel "hours"')
        gp.c('set ylabel "percent"')
        gp.c('plot "tmp.dat" w lp')

    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()