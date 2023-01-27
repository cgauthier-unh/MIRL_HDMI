#! /usr/bin/python

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# make_spec_and_time_xy.py
# Chrystal Moser, UNH
# Last Update: Aug 9, 2022
#
# This program displays two types of plots: a summary plot of a 1 hour period for the ULF
# system, or a Real-Time Display of the data being collected by the data acquisition system
#
# Parameters:
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

ans1 = sys.argv[1]

# full screen plot
mng = plt.get_current_fig_manager()
mng.full_screen_toggle()

# Define frequencies
sampling_frequency = 10 #Hz
int_step = 2**7 # number of points in each FFT

if ans1 == "pph":
    #name = input("Enter Data File Name: ")
    name = sys.argv[2]
    filename = "/home/pi-unh-hdmi/ULF/Data_Files/" + name

    # load data and find point 1 minute ago
    data = np.loadtxt(filename, dtype='float')
    data_Vx = [(data[i,1]/4096)*2.5 for i in range(len(data))]
    data_Vy = [(data[i,2]/4096)*2.5 for i in range(len(data))]

    # Plotting
    ax1 = plt.subplot(2,2,1)
    ax1.plot(data[:,0], data_Vx, 'b.-')
    plt.ylabel("X Voltage [V]")
    plt.xlabel("Time")
    plt.suptitle(name)
    plt.ylim(0, 2.5)
    plt.xlim(data[0,0], data[-1,0])

    ax2 = plt.subplot(2,2,3, sharex=ax1)
    Pxx, freqsx, binsx, imx = ax2.specgram(data_Vx, NFFT = int_step, noverlap = 0, Fs = sampling_frequency, xextent=(data[0,0], data[-1,0]), cmap='jet', vmin=-60, vmax=20)
    # --Pxx: the spectrogram
    # --freqs: the frequency vector
    # --bins: the centers of the time bins
    # --im: the .image.AxesImage instance representing the data in the plot
    plt.ylim(0, 2)
    plt.xlabel("Time" )
    plt.ylabel("X Freq [Hz]")
    
    ax3 = plt.subplot(2,2,2)
    ax3.plot(data[:,0], data_Vy, 'b.-')
    plt.ylabel("Y Voltage [V]")
    plt.xlabel("Time")
    plt.ylim(0, 2.5)
    plt.xlim(data[0,0], data[-1,0])

    ax4 = plt.subplot(2,2,4, sharex=ax3)
    Pyy, freqsy, binsy, imy = ax4.specgram(data_Vy, NFFT = int_step, noverlap = 0, Fs = sampling_frequency, xextent=(data[0,0], data[-1,0]), cmap='jet', vmin=-60, vmax=20)
    # --Pxx: the spectrogram
    # --freqs: the frequency vector
    # --bins: the centers of the time bins
    # --im: the .image.AxesImage instance representing the data in the plot
    plt.ylim(0, 2)
    plt.colorbar(imy,ax=(ax3,ax4), aspect=40, fraction=0.01)
    plt.xlabel("Time" )
    plt.ylabel("Y Freq [Hz]")

    plt.show()


if ans1 == "rtd":
    k = 0
    #ans2 = input("Time interval to display (sec)? ")
    ans2 = sys.argv[2]
    ans2 = int(ans2)

    while 1:
        list_of_files = glob.glob('/home/pi-unh-hdmi/ULF/Data_Files/*.txt')
        filename = sorted(list_of_files, key=os.path.getctime)[-1]
        while os.stat(filename).st_size == 0:
            print("Not recieving data yet, Please wait 1 minutes...")
            time.sleep(60)
        
        try:
            data = np.loadtxt(filename, dtype='float')
        except:
            os.remove(filename)
            list_of_files = glob.glob('/home/pi-unh-hdmi/ULF/Data_Files/*.txt')
            filename = sorted(list_of_files, key=os.path.getctime)[-1]
            
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
                time.sleep(ans2)
                data = np.loadtxt(filename, dtype='float')
                ind_st = np.argwhere(data[:,0] == round(data[-1,0]-ans2,1))
                while not np.any(ind_st):
                    ind_st = np.argwhere(data[:,0] == round(data[-1,0]-ans2,1))
                ind_st = ind_st[0][0]
                data_Vx = [(data[i,1]/4096)*2.5 for i in range(ind_st,len(data))]
                data_Vy = [(data[i,2]/4096)*2.5 for i in range(ind_st,len(data))]
                data_t = data[ind_st:,0]
            else:
                ind_st_prev = ind_st_prev[0][0]
                data_Vx_prev = [(data_prev[i,1]/4096)*2.5 for i in range(ind_st_prev,len(data_prev))]
                data_Vx = [(data[i,1]/4096)*2.5 for i in range(len(data))]
                data_Vx = data_Vx_prev + data_Vx
                data_Vy_prev = [(data_prev[i,2]/4096)*2.5 for i in range(ind_st_prev,len(data_prev))]
                data_Vy = [(data[i,2]/4096)*2.5 for i in range(len(data))]
                data_Vy = data_Vy_prev + data_Vy
                data_t = np.concatenate([data_prev[ind_st_prev:,0]-(data_prev[-1,0]-data[0,0]),data[:,0]])
        else:
            ind_st = ind_st[0][0]
            data_Vx = [(data[i,1]/4096)*2.5 for i in range(ind_st,len(data))]
            data_Vy = [(data[i,2]/4096)*2.5 for i in range(ind_st,len(data))]
            data_t = data[ind_st:,0]


        # Plotting
        ax1 = plt.subplot(2,2,1)
        ax1.plot(data_t, data_Vx, 'b.-')
        plt.ylabel("X Voltage [V]")
        plt.xlabel("Time")
        plt.suptitle(filename[34:])
        plt.ylim(0, 2.5)
        plt.xlim(data_t[0], data_t[-1])

        ax2 = plt.subplot(2,2,3, sharex=ax1)
        Pxx, freqsx, binsx, imx = ax2.specgram(data_Vx, NFFT = int_step, noverlap = 0, Fs = sampling_frequency, xextent=(data_t[0], data_t[-1]), cmap='jet', vmin=-60, vmax=20)
        plt.ylim(0, 2)
        plt.xlabel("Time" )
        plt.ylabel("X Freq [Hz]")

        ax3 = plt.subplot(2,2,2, sharex=ax1)
        ax3.plot(data_t, data_Vy, 'b.-')
        plt.ylabel("Y Voltage [V]")
        plt.xlabel("Time")
        plt.ylim(0, 2.5)

        ax4 = plt.subplot(2,2,4, sharex=ax1)
        Pyy, freqsy, binsy, imy = ax4.specgram(data_Vy, NFFT = int_step, noverlap = 0, Fs = sampling_frequency, xextent=(data_t[0], data_t[-1]), cmap='jet', vmin=-60, vmax=20)
        plt.ylim(0, 2)
        plt.xlabel("Time" )
        plt.ylabel("Y Freq [Hz]")
        if k == 0:
            k = 1
            cb=plt.colorbar(imy,ax=(ax3,ax4), aspect=40, fraction=0.01, label="dB")


        plt.show(block=False)
        plt.pause(1)
        ax1.cla()
        ax2.cla()
        ax3.cla()
        ax4.cla()

    plt.show()
