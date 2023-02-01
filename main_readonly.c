//
//  main.c
//  ulfcmd
//
//  Test Controller for AAL-PIP X34 buffer ADC board
//
//

#define DAQPATH "/home/pi-unh-hdmi/ULF/Data_Files/"
#define TESTFILE "/home/pi-unh-hdmi/ULF/xyz.txt"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>     // for atoi()
#include <unistd.h>
#include <termios.h>
#include <fcntl.h>
#include <time.h>       // localtime_r(), strftime()
#include <sys/time.h> 

#define LOOPUSEC 1000000

long dumpct;
long sec;

FILE *dfile;
long record;

long rcvok;

long sendpps;
long paklen;

struct timeval rcvtime;

// scans "keyword <number>" Returns number in n;
static int match (char *key, char *str, short *n)
{
    long len;
    len = strlen(key);
    if ( ! strncmp( str, key, len ) )
    {
        *n =  atoi(&str[len]);
        return 1;
    }
    return 0;
}

unsigned char  pkt[ 100 ];
long nread;

static long waitpkt(int fd)
{
    long timeout;
    
    timeout = 11;   // wait up to 1.1sec for packet to start
    while(timeout--)
    {
        nread = read(fd,pkt,sizeof(pkt));
        if(nread>0) return nread;
        usleep(100000); // 100ms
    }
    
    //if(rcvok) printf("PACKET TIMEOUT at %ld\n",sec%3600);   // report only once
    rcvok = 0;
    return 0;    
}
char *hkname[10] = {"ph","per","lper","err","ramp","drop","flg","temp","y","y"};
long dbg;

// Open new hourly file. Make file name from rcvtime
static void newfile(void)
{
    struct tm    ttime;
    char  time_string[ 32 ], fname[ 64 ], pathname[128];
    
    if(rcvok)
    {
        localtime_r( &( rcvtime.tv_sec ), &ttime );
        strftime( time_string, 32, "%Y%m%d_%H%M", &ttime );
        snprintf( fname, sizeof( fname ), "ULF-UNH-%s.txt", time_string );
        snprintf( pathname, sizeof( pathname ), "%s%s", DAQPATH, fname );
        if(dfile) fclose(dfile);
        dfile = fopen( pathname,"wct" );
        //printf("start file %s\n",fname);
    }
    //else
     //   printf("NO INCOMING PACKETS\n");
}

// read, unpack and dump and record incoming data
static void readpkt(int fd)
{
    long x,y,z;
    long i,ns,secofhr;
        
    if(!waitpkt(fd)) return;        // wait for packet start
    gettimeofday(&rcvtime, NULL);
    
    if(nread<paklen)    // partial packet
    {
        usleep(70000); // wait 70ms for pkt to finish (should be <50ms)
        i = nread;
        nread += read(fd,&pkt[i],sizeof(pkt)-i);  // read in rest of packet
    }
    
    if(nread != paklen)
    {
        tcflush( fd, TCIFLUSH );    // discard any extra
//        printf("invalid packet size %ld at %ld\n",nread,sec%3600);
        if(nread == 30)
        {
            paklen = 30;
            //printf("Trying pakelen 30\n");
        }
        else if(nread == 50)
        {
            paklen = 50;
            //printf("Trying pakelen 50\n");
        }
        return;
    }
        
    if(!rcvok)
    {
        //printf("%ld byte packet received at %ld\n",nread,sec%3600);   // report only once
        fflush(stdout);
    }
    rcvok = 1;
    
    secofhr = rcvtime.tv_sec%3600;
    if(record && (secofhr == 0)) newfile();
    
    i=0;
    ns = 0;
    while(i<nread)
    {
        if(record) fprintf(dfile,"%4ld.%ld",secofhr,ns);  // time tag sec of hour + .1 per samp
        
        if(nread >= 30)
        {
            x = ((long)pkt[i]<<4) + ((pkt[i+1]&0xF0)>>4);
            y = (((long)pkt[i+1]&0x0F)<<8) + pkt[i+2];
            i +=3;
            if(dumpct > 0) printf("%7ld%7ld",x,y);
            if(record) fprintf(dfile,"%5ld%5ld",x,y);
        }
        if(nread == 50)
        {
            z = (short)((pkt[i]<<8) + pkt[i+1]);
            i+=2;
            if(dumpct > 0) printf("%7ld",z);
            if(record) fprintf(dfile,"%5ld",z);
        }
        if(dumpct >0 && dbg) printf(" %s",hkname[ns]);
        if(dumpct > 0) printf("\n");
        if(record) fprintf(dfile,"\n");
        ns++;
    }
    if(dumpct > 0) dumpct--;
    
    if(record)
    {
        if((sec%10) == 0)
        {
            //printf("*");
            fflush(stdout);
            fflush(dfile );
        }
    }

}
static int docmd(int ttyfd)
{
    long llen;
    short n;
    char    line[64];
    
    llen = read(0,line,sizeof(line));
    if(llen >= 0)
    {
        line[llen] = 0; // terminating nul
        
        if( match("?",line,&n ))
        {
	    printf("================Commands===================\n");
            printf("q     \t\tclose serial port and exit\n");
            printf("dmp  <n>\tdump n secs to screen\n");
            printf("rec   \t\trecord data to test file\n");
            printf("daq   \t\trecord data to hourly files\n");
            printf("st    \t\tstop data recording\n");
	    printf("===========================================\n");
        }
        else if ( match("q",line,&n ))
        {
            write(ttyfd,"r",1); // put board in wait mode so it stops sending (if spps)
            printf("close serial port..\n");
            tcflush( ttyfd, TCIFLUSH );   // clean out tty buffer
            close(ttyfd);
            printf("exit\n");
            return 0; 
        }
        else if ( match("dmp",line,&n ) )
        {
            if(n<=0) dumpct = 1;
            else dumpct = n;
        }
        else if ( match("rec",line,&n ) )
        {
            if(!record)
            {
                if(!dfile) dfile = fopen( TESTFILE,"wct" );
                printf("start recording at %ld\n",sec%3600);
                record = 1;
            }
            else printf("? recording in progress\n");
        }
        else if ( match("daq",line,&n ) )
        {
            newfile();
            record = 1;
        }
        else if ( match("st",line,&n ) )
        {
            if(record)
            {
                if(dfile) fclose(dfile);
                dfile = 0L;
                printf("stop recording at %ld\n",sec%3600);
                record = 0;
            }
        }
        else
        {
            printf("?\n");
        }
    }
    return 1;
}

int main (int argc, const char * argv[])
{
    char line[64];
    char *ttydev;
    int ttyfd;
    struct  termios com_io;
    struct timeval t0,t1,delta;
    long usec;
    
    // may need to be changed if usb is unplugged
    ttydev = "/dev/ttyUSB0";
    
    if(argc == 2) ttydev = (char *)argv[1]; // get from cmd line
    
    ttyfd = open(ttydev, O_RDWR | O_NONBLOCK | O_NOCTTY);
    
    while(ttyfd<0)
    {
        printf("tty open '%s' failed\ntty?",ttydev);
        ttydev = fgets( line, sizeof( line ), stdin );    // new name
        if(strlen(ttydev) < 4) return 0; // should be "/dev/xxx" give up on empty string
        ttydev[strlen(ttydev)-1]=0; // get rid of newline
        
        
        ttyfd = open(ttydev, O_RDWR | O_NONBLOCK | O_NOCTTY);  // try agian
    }
    
    cfmakeraw( &com_io );
    
    com_io.c_cflag = B9600 | CS8 | CLOCAL | CREAD;
    
    com_io.c_iflag = IGNPAR;
    com_io.c_oflag = 0;
    com_io.c_lflag = 0;
    com_io.c_cc[ VTIME ] = 0;     // no wait
    com_io.c_cc[ VMIN ] = 0;      // return 0 if no data avail
    
    tcflush( ttyfd, TCIFLUSH );
    
    tcsetattr( ttyfd, TCSANOW, &com_io );
    
    fcntl(0,F_SETFL,O_NONBLOCK);    // nowait on stdin
    //printf("ULF ADC TEST (? for cmd list):\n");

    rcvok = 1;
    sendpps = 0;
    paklen = 30;    // default 2 axis
    dumpct = 0;
    record = 1;
    dfile = 0L;
    
    gettimeofday(&rcvtime, NULL);
    newfile();
    while(1)
    {
        gettimeofday(&t0, NULL);
        
        if(sendpps) // request each 1 sec data packet
        {
            // send 'P' if within 1ms of integral second. 1060 is typ lag. 
            if((abs(t0.tv_usec)-1060) < 1100)
            {
                //write(ttyfd,"P",1);
                tcdrain(ttyfd);
            }
            else
            {
                //printf(".");    // skipped PPS
                fflush(stdout);
            }
        }
        
        sec = t0.tv_sec;

        readpkt(ttyfd);
        
        //if(!docmd(ttyfd))
           // return 0;   // "q" command
        
        gettimeofday(&t1, NULL);
        if(sendpps)
        {
            usleep(LOOPUSEC - t1.tv_usec); // wait for next integral sec
        }
        else
        {
            timersub(&t1,&rcvtime,&delta);
            usec = LOOPUSEC-delta.tv_usec-350000;
            //printf("wait %ld ms. rcv %d ms\n",usec/1000,rcvtime.tv_usec/1000);
            if(usec>0) usleep((unsigned)usec); // wait remainder of sec
        }
    }
    
    return 0;
}

