import network
import machine
import time
from log import log


def connect_wifi():

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    wlan=[]
    #timeout=5000

    with open( 'credentials.txt','r') as f:
        # this file should contain ssid<space>pw, one per line
        line=f.readline().strip().split()
        while line:
            wlan.append(line)
            line=f.readline().strip().split()
    for pw in wlan:    
        print('connecting to {}'.format(pw[0]), end=' ')
        #start = time.ticks_ms()
        while not sta.isconnected():
            sta.connect(*pw)        
            for i in range(5):
                print('.', end='')
                if sta.isconnected():
                    print('\n')
                    log.info('connected to wifi {}; ip is {}'.format(pw[0], sta.ifconfig()[0]))
                    break
                #todo: check timeout
                time.sleep(1)
        else: break
    log.info('starting telnet...')
    network.telnet.start()
