from machine import Pin, ADC
import uasyncio as asyncio
from log import log
class Battery:
    def __init__(self, pin=35, vmin=3.5,vmax=4.0 , update_interval=None):
        self.pin=ADC(35)
        self.pin.atten(ADC.ATTN_11DB)
        self.vmin=vmin
        self.vmax=vmax    
        self.update()    
        if update_interval is not None:
            self._interval=update_interval
            loop = asyncio.get_event_loop()
            loop.create_task(self.mainloop()) 
        

    def update(self):
        self.vbat=self.pin.read()/4095*3.9*2
        log.info("battery is at {} Volts".format(self.vbat))

    def mainloop(self):
        while self._interval is not None:
            self.update()
            await asyncio.sleep(self._interval)


    @property    
    def percentage(self):
        return min(100,int(max(0,(self.vbat-self.vmin))/(self.vmax-self.vmin)*100))

    
