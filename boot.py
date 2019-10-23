import network
import machine
import time


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
                    print('\nip is {}'.format(sta.ifconfig()[0]))
                    break
                #todo: check timeout
                time.sleep(1)
        else: break
    print('starting telnet...')
    network.telnet.start()
