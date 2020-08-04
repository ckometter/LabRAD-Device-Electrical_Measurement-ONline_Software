import os
kill_gnu_cmd = 'taskkill /IM "gnuplot.exe" /F'
plotter_output = '/plotter_output.txt'
dv_number = 10
os.system(kill_gnu_cmd)
os.system('ipython he_level_plotter.py' + ' ' + str(dv_number))
