# Helium level recorder for AMI110A
# Carlos Kometter
# Creation date 7/28/2020

import labrad
import time
from datetime import datetime, date
import os
import PyGnuplot as gp
import sys

kill_gnu_cmd = 'taskkill /IM "gnuplot.exe" /F'
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def create_file(dv, data_dir, **kwargs): # try kwarging the vfixed
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

def main(*args):
    data_dir = 'he_level'
    cxn = labrad.connect()
    dv = cxn.data_vault()
    he = cxn.helium_level_meter()
    he.select_device()

    try:
        wait_time = int(sys.argv[1])
    except:
        wait_time = 1800

    print(wait_time)

    dv_number = create_file(dv, data_dir)

    startTime = time.time()
    while True:
        he.turn_on()
        time.sleep(10)
        he_level = he.get_percent()
        time.sleep(1)
        he.turn_off()

        current_datetime = datetime.now()
        if current_datetime.hour == 0:
            dv_number = create_file(dv, data_dir)

        print("{}: Helium level at {}%.".format(current_datetime, he_level))
        if (he_level<=50):
            print(f"{bcolors.WARNING}Warning: Helium level bellow 50%.{bcolors.ENDC}")

        dv.add_ex([(time.time(), he_level)])
        os.system(kill_gnu_cmd)
        time.sleep(1)
        os.chdir("C:\\Users\\Feldman Lab\\code\\Setup_BF122019\\LabRAD-Device-Electrical_Measurement-ONline_Software-pyqt5\\DEMONS GUI\\Scripts")
        os.system('ipython he_level_plotter.py' + ' ' + str(dv_number))
        #wait_time = 120 # in s
        time.sleep(wait_time - ((time.time() - startTime) % wait_time))

if __name__ == '__main__':
    main()