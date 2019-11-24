from machine import Pin, Timer, UART
from machine import TouchPad as TouchPadBase
from math import copysign
import time
try: 
    from machine import DEC
except:
    DISABLE_ROTENC=True
import uasyncio as asyncio


class HidException(Exception):
    pass

from log import log

#from hid import RotaryEncoder
#encoder=RotaryEncoder(26,27,lambda val:print(val), 10)
#loop = asyncio.get_event_loop()
#loop.run_forever()

class RotaryEncoder( DEC):
    def __init__(self, clk, dt, cmd=None, freq=4,accel=1):
        if isinstance(clk,int):
            clk=Pin(clk)
        if isinstance(dt, int):
            dt=Pin(dt)
        super().__init__(0,clk,dt)
        self.pause()
        self.freq=freq
        self.cmd=cmd
        self.accel=accel
        loop = asyncio.get_event_loop()
        loop.create_task(self._handle_rotary_encoder())

    async def _handle_rotary_encoder(self):
        self.resume()
        self.clear()
        while True:
            val=self.count_and_clear()
            if val!=0:
                #print(val)
                #self.touched_widget.add_val(val, self, self.touch_window)
                if self.accel>1:
                    val=int(copysign(abs(val)**self.accel,val))
                if self.cmd is not None:
                    self.cmd(val)
            await asyncio.sleep(1/self.freq)              
        

#from hid import Button
#btn=Button(25,lambda hid:print('press'),lambda hid :print('hold'),lambda hid:print('release'),hold_repeat_time=.1)
class Button():
    def __init__(self,pin,press_cmd=None, hold_cmd=None, release_cmd=None, active_state=0, hold_time=2,hold_repeat_time=None):
        if isinstance(pin , int):
            self.pin=Pin(pin, mode=Pin.IN,pull=Pin.PULL_FLOAT, handler=self._handle_button, trigger=Pin.IRQ_ANYEDGE, debounce=500)
        else:
            self.pin=pin
            self.pin.init(mode=Pin.IN,pull=Pin.PULL_FLOAT, handler=self._handle_button, trigger=Pin.IRQ_ANYEDGE, debounce=500)
        self.press_cmd=press_cmd
        self.hold_cmd=hold_cmd
        self.release_cmd=release_cmd
        self.hold_time=hold_time
        self.hold_repeat_time=hold_repeat_time
        self.active_state=active_state
        self.is_active=self.pin.value()==active_state
        if self.hold_cmd is not None:
            self.set_timer()
        else:
            self.timer=None
    
    def set_timer(self):
        timernum=0
        while timernum<12:
            try:
                self.tm=Timer(timernum)
                log.info('set timer {}'.format(timernum))
                break
            except ValueError:
                timernum+=1
        else: 
            raise HidException('failed to set up timer')   

    def _handle_button(self, pin):
        val=pin.irqvalue()
        if val==self.active_state and not self.is_active: #pressed   
              
            self.is_active=True 
            if self.press_cmd is not None:
                self.press_cmd(self)
            if self.hold_cmd is not None:
                self.tm.init(period=int(self.hold_time*1000), mode=Timer.ONE_SHOT, callback=self._handle_hold)
        elif val!=self.active_state and self.is_active: #release
            self.is_active=False
            if self.release_cmd is not None:
                self.tm.deinit()
                self.release_cmd(self)

    
    def _handle_hold(self, timer):
        self.tm.deinit()
        self.hold_cmd(self)
        if self.hold_repeat_time is not None:
            self.tm.init(period=int(self.hold_repeat_time*1000), mode=Timer.PERIODIC, callback=lambda timer: self.hold_cmd(self))
#from hid import TouchPad
#touch=TouchPad(14,lambda hid:print('press'),lambda hid :print('hold'),lambda hid:print('release'),hold_repeat_time=.1)
#loop = asyncio.get_event_loop()
#loop.run_forever()

class TouchPad():
    def __init__(self,pin,press_cmd=None, hold_cmd=None, release_cmd=None, threshold=400, hold_time=2,hold_repeat_time=None, freq=10):
        if isinstance(pin , int):
            pin=Pin(pin)
        else:
            pin.init()
        self.tp=TouchPadBase(pin)
        self.press_cmd=press_cmd
        self.hold_cmd=hold_cmd
        self.release_cmd=release_cmd
        self.hold_time=int(hold_time*1000)
        if hold_repeat_time is not None:
            self.hold_repeat_time_diff=int((hold_repeat_time*1000)-self.hold_time)
        else:
            self.hold_repeat_time_diff=None
        self.threshold=threshold
        self.freq=freq
        self.is_active=self.tp.read()<self.threshold
        if self.is_active:
            self.pressed_timestamp=time.ticks_ms()
        else: self.pressed_timestamp=None

        loop = asyncio.get_event_loop()
        loop.create_task(self._handle_touch())

    
    async def _handle_touch(self):
        current_hold_repead_time_diff=0
        while True:
            val=self.tp.read()
            
            if val<self.threshold :
                if not self.is_active:
                    #print(val)
                    self.pressed_timestamp=time.ticks_ms()
                    self.is_active=True 
                    if self.press_cmd is not None:
                        self.press_cmd(self)
                elif self.hold_cmd is not None and self.pressed_timestamp is not None:
                    if time.ticks_diff(time.ticks_ms(),self.pressed_timestamp)>self.hold_time+current_hold_repead_time_diff:
                        if self.hold_repeat_time_diff is not None:
                            current_hold_repead_time_diff=self.hold_repeat_time_diff
                            self.pressed_timestamp=time.ticks_ms()
                        else:
                            current_hold_repead_time_diff=0
                            self.pressed_timestamp=None
                        self.hold_cmd(self)
            elif self.is_active: #release
                self.is_active=False
                self.pressed_timestamp=None
                current_hold_repead_time_diff=0
                if self.release_cmd is not None:
                    self.release_cmd(self)
            await asyncio.sleep(1/self.freq)      

class RFID:
    def __init__(self,rx=15,tx=2,freq=1,new_tag_cmd=None, tag_removed_cmd=None):
        self.uart=UART(1,tx=tx, rx=rx, baudrate=115200)
        self.uart.init()
        self.uart.write(b'\xAB\xBA\x00\x10\x00\x10')
        #self.uart.read()#clear buffer
        self.uart.flush()
        self.uart.any()
        self.new_tag_cmd=new_tag_cmd
        self.tag_removed_cmd=tag_removed_cmd

        self.current_id=b''
        self.waittime=max(.2,1/freq)
        self.uart.callback(UART.CBTYPE_PATTERN, self.uart_cb, pattern=b'\xcd\xdc')
        loop = asyncio.get_event_loop()
        loop.create_task(self.mainloop())

    def uart_cb(self, response):    
        #print('[RFID] {}'.format(' '.join('{:02x}'.format(x) for x in  bytearray(response[2]))))
        response=bytearray(response[2])
        if response[:2]==b'\x00\x81':
            id=response[2:-1]
            if id !=  self.current_id:
                log.info('new card "{}"'.format(' '.join('{:02x}'.format(x) for x in  id)))
                self.current_id=id
                if self.new_tag_cmd is not None:
                    self.new_tag_cmd(id)
        elif self.current_id:
            log.info('card "{}" removed'.format(' '.join('{:02x}'.format(x) for x in  self.current_id)))
            if self.tag_removed_cmd is not None:
                    self.tag_removed_cmd(self.current_id)
            self.current_id=b''
        

    async def mainloop(self):
        while True:
            self.uart.write(b'\xAB\xBA\x00\x10\x00\x10')            
            await asyncio.sleep(self.waittime-.1)

# 1>. Protocol Header: send (0xAB 0xBA)
# 2>. Return: (0xCD 0xDC)
# 3>. Address: default 0x00
# 
# 4>. Command:
# Send:
#    1). 0x10 read UID number
#    2). 0x11 write UID number (4 bytes), use default password ffffffffffff
#   3). 0x12 read specified sector
#    4). 0x13 write specified sector
#    5). 0x14 modify the password of group A or group B
#    6). 0x15 read ID number
#   7). 0x16 write T5577 number
#    8). 0x17 read all sector data (M1-1K card)
# Return:
#   1).0x81 return operation succeeded
#    2).0x80 return operation failed
# 
# 5>. Data Length: means following data length; if it’s 0, then the following data will not occur.
# 
# 6>. Data: read and written data
# Sending Data:
#   1). Read Specifie Sector: the first byte of the data represents sector; the second byte means the certain block of the sector; the third byte means A or B group password (0x0A/0x0B);
#    then it comes with password of 6 bytes.
#   2). Write Specified Sedctor: the first byte of the data represents sector; the second byte means the certain block of the sector; the third byte means A or B group password (0x0A/0x0B);
#    then it comes with password of 6 bytes and block data of 16 bytes.
#   3). Modify Password: the first byte means the certain sector; the second byte means A or B group password (0x0A/0x0B); then it comes with old password of 6 byte and new password.
# Receiving Data:
#    Read specified sector return data format, the first byte is sector; the second byte is the certain block of sector; then it comes with block data of 16 bytes.
# 
# 7>. XOR check: result of other bytes check except protocol header.

