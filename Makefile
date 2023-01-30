# Make file for main_acq with flags to use the pigpio library

main_acq: main_acq.c
	gcc -Wall -pthread -o main_acq main_acq.c -lpigpiod_if2 -lrt
