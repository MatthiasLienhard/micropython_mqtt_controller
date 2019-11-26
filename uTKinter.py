import display
from machine import PWM, RTC, Pin, DEC
import machine
import time
import uasyncio as asyncio
from math import copysign, sin, cos, pi
from log import log

def rgb(r,g,b): #invese color
    return((0xFF-b<<16) + (0xFF-g<<8) + (0xFF-r))

class GuiException(Exception):
    pass

RED=rgb(255,0,0)
GREEN=rgb(0,255,0)
BLUE=rgb(0,0,255)
YELLOW=rgb(255,255,0)
ORANGE=rgb(255,165,0)
WHITE=rgb(255,255,255)
BLACK=rgb(0,0,0)
GRAY=rgb(128,128,128)
LIGHTGRAY=rgb(211,211,211)


class Widget:
    def __init__(self, parent, bg=BLACK,fg=WHITE):
        self.parent=parent
        self.bg=bg
        self.fg=fg
        self.is_visible=False

    def draw(self,screen, win):
        log.debug('draw {} at {}'.format(self,win))
        
        self.is_visible=True# used if only one widget is updated
        if screen is not None:
            self.screen=screen
        else:
            screen=self.screen
        if win is not None:
            self.win=win
        else:
            win=self.win
        screen.setwin(*win)
        screen.set_bg(self.bg)
        screen.set_fg(self.fg)
        #screen.clearwin()
    
    def grid(self, column=0, columnspan=1,row=None, rowspan=1):      
        self.parent.grid_geom.add(self, column, columnspan, row, rowspan)
        
        
    def pack(self, *args, **kwargs):
        raise NotImplementedError('pack is not implemented (only grid)')

    def place(self, *args, **kwargs):
        raise NotImplementedError('place is not implemented (only grid)')

    def add_val(self, val, screen, win): #change by rotary encoder (or buttons)
        pass

    def select(self,  screen, win): # e.g. to toggle active state
        pass


    def deactivate(self):
        self.is_visible=False

    def on_touch(self,pos, win, screen):        
        return self, win
    def on_move(self, pos, win, screen):
        pass
    def on_release(self, pos, win, screen):
        log.info('unhandled release on {}, win ({}) at {}'.format(self,win, pos))
        pass

    #def __str__(self)

class Grid:
    def __init__(self):
        self.ncols=0
        self.widgets=[]
        self._grid=[[]]
        self.col_weights=[]
        self.row_weights=[1]

    def add(self, widget, column=0, columnspan=1,row=None, rowspan=1 ):
        if row is None:
            row=self.nrows
        if not self.is_empty(column, columnspan,row, rowspan):
            raise GuiException('specified grid is not empty')
        self.extend_grid(column+ columnspan,row+rowspan)
        self._set(len(self.widgets), column, columnspan,row, rowspan)
        self.widgets.append((widget, column, columnspan,row, rowspan))
    
    def columnconfigure(self, index, weight):
        self.col_weights[index]=weight

    def rowconfigure(self, index, weight):
        self.row_weights[index]=weight
        

    @property
    def nrows(self):
        return 0 if self.ncols==0 else len(self._grid) 

    def size(self):
        return(self.ncols, self.nrows)

    #def grid_slaves(self, row=1, column=1):
    #    idx=self._grid[row][column]          
    #    if idx is None:
    #        return None 
    #    w=self.widgets[idx]

    def slaves(self, column=None, row=None, window=None):
        log.debug('get widget at [{},{}]'.format(row, column))
        if row is None and column is None:
            widgets=self.widgets
        elif row is None:
            widgets=(self.widgets[idx] for idx in set([r[column] for r in self._grid ]) if idx is not None)
        elif column is None:
            widgets=(self.widgets[idx] for idx in set(self._grid[row]) if idx is not None)
        else:
            idx=self._grid[row][column]
            if idx is None:
                widgets=[]
            else:
                widgets=[self.widgets[idx]]
        for w,c,cs,r,rs in widgets:
            log.debug('selected {} at {},{}'.format(w,r,c))
            yield w,self.bbox(c,r,c+cs-1,r+rs-1,window)

    def is_empty(self, column, columnspan,row, rowspan):
        for i in range(row, min(row+rowspan, self.nrows) ):
            for j in range(column, min(column+columnspan, self.ncols)):
                if self._grid[i][j] is not None:
                    return False
        return True

    @staticmethod
    def _get_idx( pos_rel, weights):
        #pos_rel is between 0 and 1
        total = sum(weights)
        pos_rel*=total
        os=0
        for i,w in enumerate(weights):
            if os+w>pos_rel:
                return(i)
            os+=w

    def location(self, pos,win):   
        x=(pos[0]-win[0])/(win[2]-win[0])
        y=(pos[1]-win[1])/(win[3]-win[1])
        col=self._get_idx(x, self.col_weights)
        row=self._get_idx(y, self.row_weights)
        return (col, row)

    def bbox(self, column=None, row=None, col2=None, row2=None, win=None):
        if column is None and row is None:
            raise GuiException('specify at least one, column or row')
        if column is None:
            column=0
            col2=self.ncols-1
        if row is None:
            row=0
            row2=self.nrows-1
        if col2 is None:
            col2=column
        if row2 is None:
            row2=row

        total_x=sum(self.col_weights)
        total_y=sum(self.row_weights)
        x1=sum(self.col_weights[:column])/total_x
        x2=sum(self.col_weights[:col2+1])/total_x
        y1=sum(self.row_weights[:row])/total_y
        y2=sum(self.row_weights[:row2+1])/total_y
        if win is not None:
            x1*=(win[2]-win[0])
            x2*=(win[2]-win[0])
            y1*=(win[3]-win[1])
            y2*=(win[3]-win[1])            
            return (int(x1)+win[0],int(y1)+win[1],int(x2)+win[0],int(y2)+win[1])
        return (x1,y1,x2,y2)
        



    def extend_grid(self, ncols, nrows):
        log.debug('extend to {}x{}'.format(ncols, nrows))
        if ncols>self.ncols:
            self.col_weights+=[1]*(ncols-self.ncols)
            for r in self._grid:
                r+=[None]*(ncols-self.ncols)
            self.ncols=ncols            

        if nrows>self.nrows:
            self.row_weights+=[1]*(nrows-self.nrows)
            self._grid+=[[None]*self.ncols]*(nrows-self.nrows)
            

    def _set(self,n,  column, columnspan,row, rowspan):
        for i in range(row, row+rowspan):
            for j in range(column, column+columnspan):
                self._grid[i][j]=n





class Frame(Widget):
    def __init__(self,parent=None,  bg=BLACK,fg=WHITE):
        if parent is None and isinstance(self, display.TFT):
            raise GuiException('only the root can have no parent')
        super().__init__( parent,bg,fg)        
        self.widgets=[]
        self.grid_geom=Grid()
            
    def clear_frame(self):
        self.widgets=[]
        self.grid_geom=Grid()    

    def draw(self,screen=None, win=None):
        super().draw(screen, win)

        #self.screen.clearwin()    
        for w,widget_win in self.grid_geom.slaves(window=win):
            w.draw(screen, widget_win)
            
    def deactivate(self):
        self.is_visible=False
        for w in self.grid_geom.widgets:
            w[0].deactivate()
    
    
    def on_touch(self,pos, win, screen):    
        w,widget_win=next(self.grid_geom.slaves(*self.grid_geom.location(pos,win), window=win))
        return w.on_touch(pos, widget_win, screen)

class Menue(Widget):
    def __init__(self,parent, title_size, side=0,callback=None):
        super().__init__( parent)
        self.active=0
        self.title_size=title_size
        self.side=side #0=top, 1=left, (todo: 2=bottom, 3=right not implemented so far)
        self.callback=callback #gets called uppon page change
        self.pages=[]
    
    def get_page(self,title):
        for p in self.pages:
            if p.title==title:
                return p
        raise GuiException('page "{}" not found'.format(title))

    def add_page(self, title,title_bg=BLUE,title_fg=WHITE,bg=BLACK,fg=WHITE,side=0):
        self.pages.append(MenuePage(self,title,title_bg,title_fg,bg,fg,  side))
        return self.pages[-1]
    
    def on_touch(self, pos, win, screen):        
        if self.side==0:#top
            if pos[1]-win[1]<self.title_size:
                return self, win#(win[0], win[1], win[2], win[1]+self.title_size)
            else:
                return self.pages[self.active].on_touch(pos, (win[0], win[1]+self.title_size, win[2], win[3]), screen)
        elif self.side==1:#left
            if pos[0]-win[0]<self.title_size:
                return self, win#(win[0], win[1], win[0]+self.title_size, win[1])
            else:
                return self.pages[self.active].on_touch(pos, (win[0]+self.title_size, win[1], win[2], win[3]), screen)
        else: 
            return NotImplementedError

    def on_release(self, pos, win, screen):
        log.debug('release in menue, prev page = '+self.pages[self.active].title)
        selected= self.active
        
        if self.side==0:#top
            if pos[1]-win[1]<self.title_size:
                #determine widget
                selected=int((pos[0]-win[0])/(win[2]-win[0]+1) *len(self.pages))
        elif self.side==1:#left
            if pos[0]-win[0]<self.title_size:
                #determine widget
                selected=int((pos[1]-win[1])/(win[3]-win[1]+1)*len(self.pages))
        else: raise NotImplementedError
        self.select_page(selected,screen,win)

    def select_page(self, new_page,screen,win):
        if new_page!= self.active:
            log.info('selected '+self.pages[new_page].title)
            self.pages[self.active].deactivate()
            self.active=new_page
            self.draw(screen,win)
            if self.callback is not None:
                self.callback()

    def add_val(self, val, screen, win): #change by rotary encoder (or buttons)
        if val==0:
            return()
        new_page=int(self.active+copysign(1,val)) #get direction
        #new_page=min(len(self.pages)-1, max(0,new_page))        
        if new_page<0:
            new_page=len(self.pages)-1
        elif new_page>=len(self.pages):
            new_page=0
        self.select_page(new_page,screen,win)


    def draw(self,screen=None, win=None):
        super().draw(screen, win)
        #draw header
        if len(self.pages) ==0:
            raise GuiException('Attempt to draw menue without defining pages')
        if self.side==0:#top 
            screen.setwin(win[0],win[1],win[2],self.title_size+win[1])
            step=(win[2]-win[0])/len(self.pages)
            offset=win[0]
        elif self.side==1:#left 
            screen.setwin(win[0],win[1],win[0]+self.title_size,win[3])
            step=(win[3]-win[1])/len(self.pages)
            offset=win[1]
        else:
            raise NotImplementedError
        
        screen.set_bg(self.pages[self.active].title_bg)
        screen.set_fg(self.pages[self.active].title_fg)
        screen.clearwin()
        
        for i,p in enumerate(self.pages):
            if self.side==0:
                screen.setwin(int(offset),win[1],int(offset+step),self.title_size+win[1])
            elif self.side==1:
                screen.setwin(win[0], int(offset), win[0]+self.title_size, int(offset+step))
            screen.text(screen.CENTER, screen.CENTER,p.title)
            if i==self.active:#underline active
                length=screen.textWidth(p.title)   
                if self.side==0:
                    line_x=int((step-length)/2 )
                    line_y=int((self.title_size+screen.fontSize()[1])/2+2)
                elif self.side==1:
                    line_x=int((self.title_size-length)/2 )
                    line_y=int((step+screen.fontSize()[1])/2+2)
                screen.line(line_x,line_y,line_x+length,line_y)       
            offset+=step     
        if self.side==0:    
            self.pages[self.active].draw(screen,(win[0],win[1]+self.title_size,win[2],win[3]))
        elif self.side==1:
            self.pages[self.active].draw(screen, (win[0]+self.title_size,win[1],win[2],win[3]))

class MenuePage(Frame):
    def __init__(self, parent, title, title_bg, title_fg,bg=BLUE,fg=WHITE, side=0):
        super().__init__( parent, bg,fg)
        self.title=title
        self.title_bg=title_bg
        self.title_fg=title_fg
        
class Label(Widget):    
    def __init__(self,parent, text,decoration='{}',halign=1,valign=1):
        super().__init__(parent)
        self.halign=halign
        self.valign=valign
        if isinstance(text,Var):
            text.widgets.append(self)
        else:
            text=Var(text, self)
        self.text=text
        self.decoration=decoration
    
    def draw(self,screen=None, win=None):
        super().draw(screen, win)
        self.screen.clearwin()
        self.screen.text(self.screen.halign_const[self.halign],self.screen.valign_const[self.valign],self.decoration.format(self.text.val))
    
    def __str__(self):
        return('<{} object: {}>'.format(self.__qualname__, self.decoration.format(self.text.val)))

class Button(Label):
    def __init__(self, parent, text, command,margin=10,decoration='{}',halign=1,valign=1):
        #todo: margins, minsize, maxsize
        super().__init__(parent, text,decoration, halign,valign)
        self.command=command #must be callable

    #def on_touch(self, pos) change color

    def on_release(self, pos, win, screen):#touch and release on same widget
        #if pos is within win
        self.command()

    def select(self,  win, screen):
        self.command()
    
class Slider(Widget): 
    def __init__(self, parent,  value,is_active=True, horizontal=True, min=0, max=100, command=None,select_command=None, bg=BLACK,fg=LIGHTGRAY, active_fg=BLUE, bar_wd=4,ball_r=10 , align=1, mar=15):
        super().__init__(parent)
        if isinstance(value,Var):
            value.widgets.append(self)
        else:
            value=Var(int(value), self)
        if isinstance(is_active,Var):
            is_active.widgets.append(self)
        else:
            is_active=Var(bool(is_active), self)
        
        self.value=value #current 
        self.is_active=is_active
        self.horizontal=horizontal 
        self.min=min
        self.max=max
        self.command=command
        self.select_command=select_command
        self.bg=bg
        self.fg=fg
        self.active_fg=active_fg
        self.bar_wd=bar_wd
        self.ball_r=ball_r
        self.mar=mar
        self.align=align

    def set_val(self,value, screen, win):
        self.value=value
        #win=None #where do we get the window from?
        self.draw(screen, win)
    
    def add_val(self, val, screen, win): #change by rotary encoder (or buttons)
        newval=self.value.val+val
        if newval<self.min:
            newval=self.min
        elif newval > self.max:
            newval=self.max
        if newval != self.value.val:
            self.value.val=newval
            if self.command is not None:
                self.command(self.value)#this triggers the mqtt command

    def select(self, screen, win):
        self.is_active.val= not self.is_active.val
        if self.select_command is not None:
            self.select_command(self.is_active)


    def on_touch(self,pos, win, screen):     
        self.on_move(pos, win, screen)   
        return self, win

    def on_move(self,pos, win, screen):        
        if self.horizontal:
            pos_rel=(pos[0]-win[0]-self.mar)/(win[2]-win[0]-2*self.mar)
        else:
            pos_rel=1-(pos[1]-win[1]-self.mar)/(win[3]-win[1]-2*self.mar)
        if pos_rel<0:
            pos_rel=0
        elif pos_rel>1:
            pos_rel=1
        self.value.val=int(self.min+pos_rel*(self.max-self.min))
        log.debug ('new value {}'.format(self.value.val))
    
    def on_release(self, pos, win,screen):
        if self.command is not None:
            self.command(self.value)

    def draw(self, screen=None,win=None):
        super().draw(screen, win)
        if screen is None:
            screen=self.screen
        if win is None:
            win=self.win
        screen.clearwin()
        val_rel=(self.value.val-self.min)/(self.max-self.min)
        if self.value.val>self.min and self.is_active.val:
                fg=bg=self.active_fg
        else:
            fg=self.fg
            bg=self.bg
        if self.horizontal:#left to right
            len=win[2]-win[0]-2*self.mar
            y=int((win[3]-win[1]-self.bar_wd)/2)
            screen.rect(self.mar, y, int(val_rel*len), self.bar_wd, fg,fg)
            screen.rect(int(self.mar+val_rel*len), y, int((1-val_rel)*len), self.bar_wd, self.fg,self.fg)            
            screen.circle(int(self.mar+val_rel*len),int((win[3]-win[1])/2),self.ball_r, fg, bg)
        else: #bottom to top
            len=win[3]-win[1]-2*self.mar
            x=int((win[2]-win[0]-self.bar_wd)/2)
            screen.rect(x,self.mar,  self.bar_wd, int((1-val_rel)*len),self.fg,self.fg)
            screen.rect(x,int(self.mar+(1-val_rel)*len), self.bar_wd,int(val_rel*len),  self.fg,self.fg)
            
            screen.circle(int((win[2]-win[0])/2),int(self.mar+(1-val_rel)*len),self.ball_r, fg, bg)

        


class CheckBox(Widget):
    pass

class RadioButton(Widget):
    pass

class Switch(CheckBox):
    pass

class Chart(Widget):
    pass

class DynamicWidget(Widget):
    def __init__(self, parent):
        super().__init__(parent)
        self.is_active=False
        
    def activate(self, screen,win, interval=1):
        self.is_active=True
        self.is_visible=True
        loop = asyncio.get_event_loop()
        loop.create_task(self.mainloop(screen,win, interval)) 
    
    async def mainloop(self,screen, win, interval):
        while self.is_active and self.is_visible:
            self.update(screen,win)
            await asyncio.sleep(interval)
        self.is_active=False

    def update(self, screen, win):
        #do something
        #print('dynamic widget update is not implemented')
        self.draw(screen, win)

class Clock(DynamicWidget):

    def __init__(self,parent,  halign=1, valign=1, analog=True):
        super().__init__(parent)
        self.halign=halign
        self.valign=valign
        self.analog=analog
        RTC().ntp_sync(server="hr.pool.ntp.org", tz="CET-1CEST")
    
      
    def draw(self,screen=None, win=None):
        super().draw(screen, win)
        if screen is None:
            screen=self.screen
        if win is None:
            win=self.win

        if not self.is_active:
            self.activate(screen, win)
        screen.clearwin()
        now=time.localtime()
        if self.analog:
            center=((win[2]-win[0])//2, (win[3]-win[1])//2)
            r=int(min(*center)*.9)
            screen.circle(*center, r=r)
            screen.line(*center+ ( int(cos((now[3]-3)/12*2*pi )*r/2)+center[0], int(sin((now[3]-3)/12*2*pi )*r/2)+center[1]))#hours
            screen.line(*center+ ( int(cos((now[4]-15)/60*2*pi )*r*.8)+center[0], int(sin((now[4]-15)/60*2*pi )*r*.9)+center[1]))#min
            screen.line(*center+ ( int(cos((now[5]-15)/60*2*pi )*r*.8)+center[0], int(sin((now[5]-15)/60*2*pi )*r*.9)+center[1]))#sec
        else:            
            text='{2}.{1:02d}.{0} - {3}:{4:02d}:{5:02d} Uhr'.format(*now)
            screen.text(screen.halign_const[self.halign],screen.valign_const[self.valign],text)


class FotoFrame(Widget):
    pass


class Var:
    def __init__(self, val, widget=None, t=None):
        self.__val=val
        self.widgets=[]
        self.t=t
        if isinstance(widget, Widget):
            self.widgets.append(widget)
        
    def __get__(self, instance, owner):
        return self.__val

    def __set__(self, instance, val):
        if self.t is not None:
            if self.t==bool:
                val=str(val).lower() in ['true' ,'yes', '1', 'on', 'high']
            val=self.t(val)
        if self.__val != val:
            self.__val=val        
            for w in self.widgets:
                if w.is_visible:
                    w.draw()

    @property
    def val(self):
        return self.__val
    
    @val.setter
    def val(self, val):
        if self.t is not None:
            if self.t==bool:
                val=str(val).lower() in ['true' ,'yes', '1', 'on', 'high']
            val=self.t(val)
        if self.__val != val:
            self.__val=val        
            for w in self.widgets:
                if w.is_visible:
                    w.draw()



class Tk(display.TFT, Frame): 
    #define some colors
    halign_const=[0,display.TFT.CENTER,display.TFT.RIGHT]
    valign_const=[0,display.TFT.CENTER,display.TFT.BOTTOM]
    
    def __init__(self):
        super().__init__(self)
        self.bg=BLACK
        self.fg=WHITE
        self.clear_frame()
        self.standby_time=60
        self.shutdown_time=100
        self.wakeup_pin=None
        self.touch_calibration=(500,3500,500,3500)
        self.initiated=0
        #self.movable=False
    
   
    @property
    def height(self):
        return self.screensize()[1]
    
    
    @property
    def width(self):
        return self.screensize()[0]

    
    def init(self, *args, **kwargs) :
        if 'backl_pin' in kwargs: #interference with TFT, need to remove the parameter from **kwargs dict
            self._backl=PWM(kwargs['backl_pin'])
            self._backlight=100
            self._backl.duty(0)
            del kwargs['backl_pin']
        if 'hid' in kwargs:
            self.init_hid(kwargs['hid'])
            del kwargs['hid']
        kwargs.setdefault('rot',super().LANDSCAPE)
        super().init( *args, **kwargs)
        self.rot=kwargs['rot']
        self.timestamp=time.time()
        self.standby=False
        self.touch_start=None #start position of touch event
        self.touch_current=None #current position of touch event (eg. during touch)
        self._focus_window=None #window of currently selected widget (e.g. touched)
        self._focus_widget=None #currently selected widget -target of touch release event and rotary encoder (e.g. by touched, or selected by button press)
        self.initiated=1
        loop = asyncio.get_event_loop()
        loop.create_task(self.handle_touch())

    @property
    def focus_window(self):
        return self._focus_window if self._focus_window is not None else (0,0)+self.screensize()
    @focus_window.setter
    def focus_window(self,win):
        self._focus_window=win

    @property
    def focus_widget(self):
        return self._focus_widget if self._focus_widget is not None else self
    @focus_widget.setter
    def focus_widget(self,widget):
        self._focus_widget=widget

    def set_wakeup_pin(self, pin=None):
        if isinstance(pin, int):
            pin=Pin(pin)
        self.wakeup_pin=pin
        

    def  deinit(self):
        super().deinit()
        self.initiated=False
        #todo: led


    def clearwin(self):
        w,h=self.winsize()
        self.rect(0,0,w,h,self.get_bg(), self.get_bg())

    
    async def handle_touch(self, freq=20):
        self.timestamp=time.time()
        while self.initiated:
            t,x, y=self.gettouch()
            if t and self.touch_start is None: #touch_down
                self.timestamp=time.time()
                log.debug('touch at ({},{})'.format(x,y))
                self.touch_start=x,y
                self.touch_current=x,y
                self._focus_widget,self._focus_window =self.on_touch((x,y), (0,0,self.width, self.height), self)
                self.debounce=0                
            elif t and self.touch_start is not None:#touch_move
                self.touch_current=(x,y)
                #if self.focus_widget.is_movable: #this is set by the widget at touch_down
                #self.focus_widget.on_move((x-self.focus_window[0], y-self.focus_window[1]), self.focus_window)
                self.focus_widget.on_move(self.touch_current, self.focus_window, self)
            elif not t and self.touch_start is not None:#touch release
                log.debug('release at ({},{})'.format(*self.touch_current))
                #self.movable=False
                self.focus_widget.on_release(self.touch_current, self.focus_window, self)
                self.touch_start=None
                self.touch_current=None
            if time.time()-self.timestamp > self.shutdown_time:
                self.shutdown()
            elif time.time()-self.timestamp > self.standby_time:
                if not self.standby:
                    self.set_standby()
            elif self.standby:
                self.wakeup()
            await asyncio.sleep(1/freq)  

    def set_standby(self):
        if not self.standby:
            self._backlight=self.backlight()
            log.info('going to standby')
            self.backlight(0)
            self.tft_writecmd(0x10) #standby
            self.standby=True
    def wakeup(self):
        if self.standby:
            self.tft_writecmd(0x11) #wake up
            self.backlight(self._backlight)
            self.standby=False
            log.info('waking from standby')

    def shutdown(self):
        self.set_standby()
        log.info('shutdown ...')
        if self.wakeup_pin is not None:
            rtc=RTC()
            rtc.wake_on_ext0(self.wakeup_pin, 0)
        machine.deepsleep()

    #command functions for hid
    def cmd_add(self, val=1):
        self.timestamp=time.time()
        self.focus_widget.add_val(val, self, self.focus_window)

    def cmd_sub(self, val=1):
        self.timestamp=time.time()
        self.focus_widget.add_val(-val, self, self.focus_window)


    def cmd_toggle_fullscreen(self):
        self.timestamp=time.time()
        pass #todo: collapse menues

    def cmd_select(self):
        self.timestamp=time.time()
        self.focus_widget.select( self, self.focus_window)
    
    def cmd_back(self):
        self.timestamp=time.time()
        pass #todo: go one level back 


    def backlight(self, *arg): #control backlight
        return self._backl.duty(*arg) 

    def orient(self, rot=None):
        if rot is not None:
            super().orient(rot)
            self.rot=rot
        return self.rot

    def calibrate_touch(self):
        raise NotImplementedError
        #todo:calibration

    def gettouch(self,raw=False):
        
        cal=self.touch_calibration
        res=self.screensize()
        t,y,x=super().gettouch(raw=True)
        if raw:
            return(t,x,y)
        if not t or x<cal[0] or x>cal[1] or y<cal[2] or y>cal[3]: #maybe better return extremes
            return False,0,0
        #do calibration
        x=((x-cal[0])/(cal[1]-cal[0]))*res[0]
        y=((y-cal[2])/(cal[3]-cal[2]))*res[1]
        if self.orient() in [display.TFT.PORTRAIT,display.TFT.PORTRAIT_FLIP]: 
            (x,y)=(y,x)
        if self.orient() in [display.TFT.LANDSCAPE_FLIP,display.TFT.PORTRAIT_FLIP]:
            y=res[1]-y
        return(t,int(x),int(y))

    def draw(self):
        super().draw(self, (0,0,self.width, self.height) )
    #    if self.focus_window is not None:
    #        self.rect(*self.focus_window, color=RED)
    
    def mainloop(self):
        self.draw()
        #start async loop for touch
        loop = asyncio.get_event_loop()
        try: 
            loop.run_forever()
        except Exception as e:
            self.clear()
            self.resetwin()
            self.text(self.CENTER, self.CENTER, '{}'.format(e))
            log.exception('exception in root.mainloop()',e)
            raise e

    #def refresh(self):
        #refresh the screen
    #    self.screen.


