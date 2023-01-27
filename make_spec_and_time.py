#! /usr/bin/python

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# make_spec_and_time.py
# Chrystal Moser, UNH
# Last Update: July 18, 2022
#
# This program displays two types of plots: a summary plot of a 1 hour period for the ULF
# system, or a Real-Time Display of the data being collected by the data acquisition system
#
# Parameters:
#	axis to plot: "x" or "y"
#	type of plot: "pph" (plot previous hour) or "rtd" (real time display)
#	time interval: data file name (e.g "ULF-20220718_1500.txt" for pph) or seconds (e.g. "300" for rtd)
# Output:
#	full screen plot of time series and corresponding spectrogram
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Import Libraries
import numpy as np
import matplotlib.pyplot as plt
import time
import sys
import glob
import os
import warnings
warnings.filterwarnings("ignore")

#ans0 = input("Which axis would you like to plot (x or y)? ")
ans0 = sys.argv[1]
if ans0 == "x":
    col = 1
elif ans0 == "y":
    col = 2
else:
    print("Invalid response")
    sys.exit()

#ans1 = input("Would you like a real time display (rtd) or plot previous hour (pph)? ")
ans1 = sys.argv[2]

# full screen plot
mng = plt.get_current_fig_manager()
mng.full_screen_toggle()

# Define frequencies
sampling_frequency = 10 #Hz
int_step = 2**7 # number of points in each FFT

if ans1 == "pph":
    #name = input("Enter Data File Name: ")
    name = sys.argv[3]
    filename = "/home/pi-unh-hdmi/ULF/Data_Files/" + name

    # load data and find point 1 minute ago
    data = np.loadtxt(filename, dtype='float')
    data_V = [(data[i,col]/4096)*2.5 for i in range(len(data))]

    # Plotting
    ax1 = plt.subplot(2,1,1)
    ax1.plot(data[:,0], data_V, 'b.-')
    plt.ylabel("Voltage [V]")
    plt.xlabel("Time")
    plt.title(filename[32:] + " " + ans0+"-axis")
    plt.ylim(0, 2.5)
    plt.xlim(data[0,0], data[-1,0])

    ax2 = plt.subplot(2,1,2, sharex=ax1)
    Pxx, freqs, bins, im = ax2.specgram(data_V, NFFT = int_step, noverlap = 0, Fs = sampling_frequency, xextent=(data[0,0], data[-1,0]), cmap='jet', vmin=-60, vmax=0)
    # --Pxx: the spectrogram
    # --freqs: the frequency vector
    # --bins: the centers of the time bins
    # --im: the .image.AxesImage instance representing the data in the plot
    plt.ylim(0, 2)
    plt.colorbar(im,ax=(ax1,ax2), aspect=40, fraction=0.01)
    plt.xlabel("Time" )
    plt.ylabel("Freq [Hz]")

    plt.show()


if ans1 == "rtd":
    k = 0
    #ans2 = input("Time interval to display (sec)? ")
    ans2 = sys.argv[3]
    ans2 = int(ans2)

    while 1:
        list_of_files = glob.glob('/home/pi-unh-hdmi/ULF/Data_Files/*.txt')
        filename = max(list_of_files, key=os.path.getctime)
        data = np.loadtxt(filename, dtype='float')

        ind_st = np.argwhere(data[:,0] == round(data[-1,0]-ans2,1))
        if not np.any(ind_st):
            filename2 = sorted(list_of_files, key=os.path.getctime)[-2]
            data_prev = np.loadtxt(filename2, dtype='float')
            tot_time = data[-1,0] - data[0,0]
            new_file_first_sec = int(filename.split('_')[2].split('.')[0][0:2])*60*60 + int(filename.split('_')[2].split('.')[0][2:])*60 + data[0,0]
            prev_file_last_sec = int(filename2.split('_')[2].split('.')[0][0:2])*60*60 + int(filename2.split('_')[2].split('.')[0][2:])*60 + data_prev[-1,0]
            ind_st_prev = np.argwhere(data_prev[:,0] == round(data_prev[-1,0]-(ans2-tot_time),1))
            if not np.any(ind_st_prev) or (new_file_first_sec - prev_file_last_sec) > 0.1:
                print("Waiting for file to load enough data...")
                time.sleep(ans2-data[-1,0]+data[0,0]+15)
                data = np.loadtxt(filename, dtype='float')
                ind_st = np.argwhere(data[:,0] == round(data[-1,0]-ans2,1))
                ind_st = ind_st[0][0]
                data_V = [(data[i,col]/4096)*2.5 for i in range(ind_st,len(data))]
                data_t = data[ind_st:,0]
            else:
                ind_st_prev = ind_st_prev[0][0]
                data_V_prev = [(data_prev[i,col]/4096)*2.5 for i in range(ind_st_prev,len(data_prev))]
                data_V = [(data[i,col]/4096)*2.5 for i in range(len(data))]
                data_V = data_V_prev + data_V
                data_t = np.concatenate([data_prev[ind_st_prev:,0]-(data_prev[-1,0]-data[0,0]),data[:,0]])
        else:
            ind_st = ind_st[0][0]
            data_V = [(data[i,col]/4096)*2.5 for i in range(ind_st,len(data))]
            data_t = data[ind_st:,0]

        # plotting
        ax1 = plt.subplot(2,1,1)
        ax1.plot(data_t, data_V, 'b.-')
        plt.title(filename[13:] + " " + ans0+"-axis")
        plt.ylabel("X Voltage [V]")
        plt.xlabel("Time")
        plt.autoscale(False)
        plt.ylim(0, 2.5)
        plt.xlim(data[ind_st,0], data[-1,0])

        ax2 = plt.subplot(2,1,2, sharex=ax1)
        Pxx, freqs, bins, im = ax2.specgram(data_V, NFFT = int_step, noverlap = 0, Fs = sampling_frequency, xextent=(data_t[0], data_t[-1]), cmap='jet', vmin=-60, vmax=0)
        plt.xlabel("Time" )
        plt.ylabel("Freq [Hz]")
        plt.ylim(0, 2)
        if k == 0:
            k = 1
            cb=plt.colorbar(im,ax=(ax1,ax2), aspect=40, fraction=0.01, label="dB")


        plt.show(block=False)
        plt.pause(1)
        ax1.cla()
        ax2.cla()

    plt.show()
