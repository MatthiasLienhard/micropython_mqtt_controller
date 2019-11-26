try:
    import uasyncio as asyncio
except ImportError:
    connect_wifi()
    import upip
    print('installing asyncio')
    upip.install('micropython-uasyncio', '.')
    upip.install('micropython-uasyncio.synchro', '.')
    upip.install('micropython-uasyncio.queues', '.')
    import uasyncio as asyncio
    
import time, math
from machine import SPI, PWM, Pin
from time import sleep
import uTKinter as tk
import network
from utils import Battery

from hid import Button ,TouchPad,RotaryEncoder, RFID
from log import log

root = tk.Tk()

#touch=TouchPad(14,lambda hid:print('press'),lambda hid :print('hold'),lambda hid:print('release'),hold_repeat_time=.1)
btn=Button(25,lambda hid:log.info('press'),lambda hid :log.info('hold'),lambda hid :root.cmd_select(),hold_repeat_time=.1)
encoder=RotaryEncoder(26,27,lambda val: root.cmd_add(val), freq=5)
root.set_wakeup_pin(25) # to wakeup from deepsleep

root.init(root.ILI9488, width=240, height=320, 
    miso=19, mosi=23, clk=18, cs=5, dc=21, tcs=0,rst_pin=22, backl_pin=4, bgr=False,
    hastouch=root.TOUCH_XPT,backl_on=1, speed=40000000, splash=False, rot=root.LANDSCAPE_FLIP)

#info=gui.Frame(root, bg=screen.BLACK, fg=screen.WHITE)
tk.Label(root, 'Starting wifi...').grid()
root.backlight(100)
root.draw()
connect_wifi()

mqtt = network.mqtt('home_controller', 'mqtt://192.168.178.65')
mqtt.start()

rooms=[('Wohnzi.',[4,7,8]), ('Schlafzi.',[2,3]), ('Bastelzi.',[1,6])]
lights=dict()


def datacb(msg):
    log.debug("[{}] Data arrived from topic: {}, Message:\n".format(msg[0], msg[1]), msg[2])
    topic=msg[1].split('/')
    if len(topic)==3 and topic[0]=='node-red' and topic[1]=='lights' and msg[2]!='get_state':
        log.info('update for light {}: {}'.format(topic[2], msg[2]))
        val=msg[2].split('/')
        lnr=int(topic[2])
        if lnr in lights:            
            lights[lnr][0].val=val[0]#bri
            lights[lnr][1].val=val[1]#on/off



root.clear_frame()
top_menue=tk.Menue(root, 60, side=1)
top_menue.grid()

licht_page=top_menue.add_page(title='Licht', title_fg=tk.BLACK, title_bg=tk.YELLOW)
licht_menue=tk.Menue(licht_page, 60, side=0)
licht_menue.grid()

musik_page=top_menue.add_page(title='Musik', title_fg=tk.WHITE, title_bg=tk.RED)
musik_frame=tk.Label(musik_page,'hier steuert man die anlage')
musik_frame.grid()

wetter_page=top_menue.add_page(title='Wetter', title_fg=tk.WHITE, title_bg=tk.BLUE)
wetter_frame=tk.Label(wetter_page,'bestimmt bald wieder gut')
wetter_frame.grid()

uhr_page=top_menue.add_page(title='Uhr', title_fg=tk.BLACK, title_bg=tk.GREEN)
uhr_frame=tk.Clock(uhr_page)
uhr_frame.grid()

settings_page=top_menue.add_page(title='Settings', title_fg=tk.BLACK, title_bg=tk.YELLOW)

bat=Battery(pin=35, update_interval=600) #send status every 10 minutes
vbat=tk.Var(bat.vbat)
bat.vbat=vbat.val
tk.Label(settings_page, bat.vbat, decoration='Battery: {:.2} Volt').grid(columnspan=3)
tk.Label(settings_page, 'Hintergrundbeleuchtung').grid(columnspan=3)

bgled=tk.Var(100)
tk.Slider(settings_page,bgled,min=1, command=lambda x: root.backlight(x.val)).grid(columnspan=2, row=2)
tk.Label(settings_page,bgled, decoration='{}%').grid(column=2, row=2)


foto_page=top_menue.add_page(title='Fotos', title_fg=tk.WHITE, title_bg=tk.RED)
tk.Label(foto_page, 'Fotos').grid()

for r in rooms:
    page=licht_menue.add_page(title=r[0], side=0, title_fg=tk.BLACK, title_bg=tk.YELLOW)
    for row,id in enumerate(r[1]):
        log.debug('add new light {} in room {}'.format(id, r[0]))
        #print('deconz/lights/{}/state'.format(id))
        topic='controller/lights/{}/state'.format(id)
        #lf=tk.Frame(side=1)
        #page.pack(lf)
        lights[id]=(tk.Var(0, t=bool),tk.Var(0, t=int), topic)
        tk.Label(page, id, decoration='L{}: ').grid(row=row, column=0)

        tk.Slider(page, lights[id][1], lights[id][0],
            command=lambda x,topic=topic: mqtt.publish(topic, str(x.val)), 
            select_command=lambda x,topic=topic: mqtt.publish(topic, 'on' if x.val else 'off')
                ).grid(row=row, column=1, columnspan=4)
        tk.Label(page, lights[id][1], decoration='{}%').grid(row=row, column=5 )

rfid=RFID(rx=15,tx=2,freq=1,new_tag_cmd=lambda x,topic='audio/cmd/play': mqtt.publish(topic, str(x)), tag_removed_cmd=lambda x,topic='audio/cmd/stop': mqtt.publish(topic, str(x)))

mqtt.config(data_cb=datacb)
#mqtt.status()
mqtt.subscribe('node-red/#')
mqtt.subscribe('audio/#')
mqtt.subscribe('web/weather')

mqtt.publish('controller/lights/all/state', 'get')
#mqtt.publish('deconz/groups/all/state', 'get')
#mqtt.publish('homecontroller/status/', '1')

root.mainloop()
#mqtt.free()

#import requests
#import ujson
#resp=requests.get("http://api.openweathermap.org/data/2.5/forecast?id=2950159&APPID=e60bd2ef873877646f89f5815aa38a5d")
#wetter=ujson.loads(resp[2])
#[l['main']['temp']-273.15 for l in wetter['list']]