# Make file for main_acq with flags to use the pigpio library

main_ro: main_readonly.c
	gcc -Wall -pthread -o main_ro main_readonly.c 

