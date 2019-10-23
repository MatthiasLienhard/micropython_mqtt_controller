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
import microgui as gui
import network
screen = gui.MicroGUI()
screen.add_rotary_encoder(Pin(14), Pin(12))
screen.init(screen.ILI9488, width=240, height=320, 
    miso=19, mosi=23, clk=18, cs=5, dc=21, tcs=0,rst_pin=4, backl_pin=22, bgr=False,
    hastouch=screen.TOUCH_XPT,backl_on=1, speed=40000000, splash=False, rot=screen.LANDSCAPE_FLIP)

screen.root=gui.Frame(bg=screen.BLACK, fg=screen.WHITE)
screen.root.pack(gui.Label('Starting wifi...'))
screen.draw()
connect_wifi()

mqtt = network.mqtt('home_controller', 'mqtt://192.168.178.65')
mqtt.start()
mqtt.status()
mqtt.subscribe('lights/#')
mqtt.subscribe('audio/#')
mqtt.subscribe('web/weather')
rooms=['Wohnzi.', 'Schlafzi.', 'Bastelzi.']

lights={'lights/Bastelzimmer/bulb1/brightness':gui.Var(0)}

def datacb(msg):
    print("[{}] Data arrived from topic: {}, Message:\n".format(msg[0], msg[1]), msg[2])
    if msg[1] in lights:        
        lights[msg[1]].val=int(msg[2])


mqtt.config(data_cb=datacb)
mqtt.publish('statusrequest/lights', 'get')
mqtt.publish('homecontroller/status/', '1')

top_menue=gui.Menue(60, side=1)
screen.root=top_menue
licht=top_menue.add_page(title='Licht', title_fg=screen.BLACK, title_bg=screen.YELLOW)
licht_menue=gui.Menue(60, side=0)
licht.pack(licht_menue)
musik=top_menue.add_page(title='Musik', title_fg=screen.WHITE, title_bg=screen.RED)
musik.pack(gui.Label('hier steuert man die anlage'))
wetter=top_menue.add_page(title='Wetter', title_fg=screen.WHITE, title_bg=screen.BLUE)
wetter.pack(gui.Label('bestimmt bald wieder gut'))
uhr=top_menue.add_page(title='Uhr', title_fg=screen.BLACK, title_bg=screen.GREEN)
uhr.pack(gui.Clock())
settings=top_menue.add_page(title='Settings', title_fg=screen.BLACK, title_bg=screen.YELLOW)
settings.pack(gui.Label('Hintergrundbeleuchtung'))
settings.pack(gui.Frame(side=1))
bgled=gui.Var(100)
settings.widgets[-1].pack(gui.Slider(bgled,min=1, command=lambda x: screen.backlight(x.val)), size=5)
settings.widgets[-1].pack(gui.Label(bgled, decoration='{}%'))
settings.pack(gui.Label('weitere Einstellungen'), size=4)


fotos=top_menue.add_page(title='Fotos', title_fg=screen.WHITE, title_bg=screen.RED)
fotos.pack(gui.Label('Fotos'))


wz=licht_menue.add_page(title='Wohnzi.', side=0, title_fg=screen.BLACK, title_bg=screen.YELLOW)
lichter=[]
for l in range(2):
    lf=gui.Frame(side=1)
    wz.pack(lf)
    lval=gui.Var(0)
    lf.pack(gui.Label(l+1, decoration='L{}: '))
    lf.pack(gui.Slider(lval), size=4)
    lf.pack(gui.Label(lval, decoration='{}%'))

sz=licht_menue.add_page(title='Schlafzi.', title_fg=screen.BLACK, title_bg=screen.YELLOW)
#z.pack(gui.Label('Bastelzimmer'))
sz.pack(gui.Menue(60,side=1))
submenue=sz.widgets[0]
for i in range(3):
    page=submenue.add_page(title= 'Licht {}'.format(i+1), title_bg=screen.RED,side=1)
    #page.pack(gui.Label('Licht {} Steuerung'.format(i+1)))
    for l in range(2):
        lf=gui.Frame(side=0)
        page.pack(lf)
        lval=gui.Var(0)
        lf.pack(gui.Label(l+1, decoration='L{}: '))
        lf.pack(gui.Slider(lval, horizontal=False), size=4)
        lf.pack(gui.Label(lval, decoration='{}%'))


bz=licht_menue.add_page(title='Balstelzi.', side=0,title_fg=screen.BLACK,title_bg=screen.YELLOW)
lval=lights['lights/Bastelzimmer/bulb1/brightness']
bz.pack(gui.Button('light', margin=10, command=lambda: mqtt.publish('lights/Bastelzimmer/bulb1/toggle', '1')))
bz.pack(gui.Slider(lval, horizontal=True, command=lambda x: mqtt.publish('lights/Bastelzimmer/bulb1/brightness', str(x.val))), size=4)
bz.pack(gui.Label(lval, decoration='{}%'))
screen.mainloop()
#mqtt.free()

#import requests
#import ujson
#resp=requests.get("http://api.openweathermap.org/data/2.5/forecast?id=2950159&APPID=e60bd2ef873877646f89f5815aa38a5d")
#wetter=ujson.loads(resp[2])
#[l['main']['temp']-273.15 for l in wetter['list']]