# Make file for main_acq with flags to use the pigpio library

main_acq: main_acq.c
	gcc -Wall -pthread -o main_ro main_readonly.c 

