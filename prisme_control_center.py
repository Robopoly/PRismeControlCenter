#!/usr/bin/env python
# -*- coding: utf-8 -*-

# threading required to update UI asynchronously
import wx, string, time, serial, threading, subprocess
# for linear camera data plotting
from wx.lib.plot import PolyLine, PlotCanvas, PlotGraphics

__author__ = "Karl Kangur"
__copyright__ = "Copyright 2013, Robopoly"
__credits__ = ["Karl Kangur"]
__license__ = "GPL"
__version__ = "1"
__maintainer__ = "Robopoly"
__email__ = "robopoly@epfl.ch"
__status__ = "Development"

linearCameraData = []
irSensorData = []
serialComm = 0
updateFlag = 0
commQueue = []
endComm = 0

# called event when the user interface needs updating
EVENT_UPDATE = wx.NewEventType()
EVENT_RESET = wx.NewEventType()
EVENT_DISCONNECTED = wx.NewEventType()

# communication thread class
class commThread(threading.Thread):
    def __init__(self, parent, value):
        threading.Thread.__init__(self)
        self._parent = parent
    
    def disconnect(self):
        global serialComm
        self.send('r')
        serialComm.close()
        serialComm = 0
    
    def send(self, data):
        global serialComm
        serialComm.write('d')
        serialComm.flush()
    
    def get(self, size):
        global serialComm
        
        try:
            data = serialComm.read(size=size)
        except OSError:
            # called when user disconnects device without telling the application
            self._parent.scanDevices(EVENT_DISCONNECTED)
            wx.MessageBox('Connection error', 'Error', wx.OK|wx.ICON_ERROR)
            # rescan devices list to remove disconnected device
            self._parent.uiReset(EVENT_DISCONNECTED)
            return False
        
        # data length must match, or is considered as faulty connection
        if len(data) < size:
            wx.PostEvent(self._parent, wx.PyCommandEvent(EVENT_DISCONNECTED, -1))
            self.disconnect()
            return False
        return data

    def run(self):
        global linearCameraData, irSensorData, updateFlag, endComm, serialComm, commQueue
        while serialComm:
            if endComm == 1:
                # reset (stop) the device
                self.disconnect()
                endComm = 0
                wx.PostEvent(self._parent, wx.PyCommandEvent(EVENT_RESET, -1))
                break
        
            # check if some other data has to be sent
            if len(commQueue) > 0:
                serialComm.write(commQueue[0])
                serialComm.flush()
                commQueue.pop(0)
        
            # ask for data
            serialComm.write('d')
            serialComm.flush()
            
            # read linear camera data, parse and format for graph
            data = self.get(102)
            if not data: break
            
            linearCameraData = []
            for i in range(0, len(data)):
                linearCameraData.append([i, ord(data[i])])
            
            # get IR sensor data and parse
            data = self.get(5)
            if not data: break
            
            irSensorData = []
            for i in range(0, len(data)):
                irSensorData.append(str(ord(data[i])))
            
            # check if parent still exists (if user closes the window without disconnecting)
            if isinstance(self._parent, wx._core._wxPyDeadObject):
                self.disconnect()
                break
            
            # dispatch event to parent
            wx.PostEvent(self._parent, wx.PyCommandEvent(EVENT_UPDATE, -1))
            
            # wait loop until the UI has been updated
            updateFlag = 1
            while updateFlag == 1:
                time.sleep(0.01)

class Control(wx.Frame):
    def __init__(self, parent, title):
        super(Control, self).__init__(parent, title=title, size=(700, 600))
        # default speed value
        self.speed = 20
        self.lastGo = 0
        # create the window
        self.InitUI()
        self.Centre()
        self.SetTitle('PRisme Control Center')
        self.Show()
    
    def uiUpdate(self, event):
        global updateFlag
        # update graph
        self.canvas.Draw(self.drawLinearCameraOutput(), xAxis=(0,102), yAxis=(0,255))
        
        # update graph values
        self.st_peak.SetLabel(str(self.peakIntensity))
        self.st_max.SetLabel(str(self.maxIntensity))
        self.st_min.SetLabel(str(self.minIntensity))
        self.st_delta.SetLabel(str(self.deltaIntensity))
        self.st_avg.SetLabel(str(self.avgIntensity))
        
        # update IR sensor values
        ir0 = int(irSensorData[0])
        self.ir_0.SetValue(irSensorData[0])
        self.ir_0.SetBackgroundColour((255, ir0, ir0))
        ir1 = int(irSensorData[1])
        self.ir_1.SetValue(irSensorData[1])
        self.ir_1.SetBackgroundColour((255, ir1, ir1))
        ir2 = int(irSensorData[2])
        self.ir_2.SetValue(irSensorData[2])
        self.ir_2.SetBackgroundColour((255, ir2, ir2))
        ir3 = int(irSensorData[3])
        self.ir_3.SetValue(irSensorData[3])
        self.ir_3.SetBackgroundColour((255, ir3, ir3))
        ir4 = int(irSensorData[4])
        self.ir_4.SetValue(irSensorData[4])
        self.ir_4.SetBackgroundColour((255, ir4, ir4))
        updateFlag = 0

    def uiReset(self, event):
        global linearCameraData
        # reset user interface
        linearCameraData = []
        self.canvas.Draw(self.drawLinearCameraOutput(), xAxis=(0,102), yAxis=(0,255))
        
        # reset go instruction
        self.lastGo = 0
        
        # update graph values
        self.tc_intTime.SetValue("0")
        self.st_peak.SetLabel("0")
        self.st_max.SetLabel("0")
        self.st_min.SetLabel("0")
        self.st_delta.SetLabel("0")
        self.st_avg.SetLabel("0")
        
        # update IR sensor values
        self.ir_0.SetValue("0")
        self.ir_0.SetBackgroundColour('white')
        self.ir_1.SetValue("0")
        self.ir_1.SetBackgroundColour('white')
        self.ir_2.SetValue("0")
        self.ir_2.SetBackgroundColour('white')
        self.ir_3.SetValue("0")
        self.ir_3.SetBackgroundColour('white')
        self.ir_4.SetValue("0")
        self.ir_4.SetBackgroundColour('white')
    
        # disable controls
        self.b_setIntTime.Disable()
        self.b_forwards.Disable()
        self.b_back.Disable()
        self.b_left.Disable()
        self.b_right.Disable()
        self.b_stop.Disable()
        
        self.b_toggleConnect.SetLabel("Connect")

    def getDevices(self):
        self.devices = string.split(subprocess.Popen("ls /dev/tty.*", stdout=subprocess.PIPE, shell=True).communicate()[0], "\n")

    def drawLinearCameraOutput(self):
        global linearCameraData
        graphs = []
        
        # the actual linear camera data
        output = PolyLine(linearCameraData, legend= 'Linear camera data', colour='red')
        graphs.append(output)
        
        # find the peak, maximum, minimum and average values
        peakLeft = 0
        self.minIntensity = 255
        peakRight = 0
        peakIleft = 0
        peakIright  = len(linearCameraData) - 1
        self.avgIntensity = 0
        for i in range(0, len(linearCameraData)):
            if linearCameraData[i][1] > peakLeft:
                peakLeft = linearCameraData[i][1]
                peakIleft = i
            if linearCameraData[len(linearCameraData) - i - 1][1] > peakRight:
                peakRight = linearCameraData[len(linearCameraData) - i - 1][1]
                peakIright = len(linearCameraData) - i - 1
            if linearCameraData[i][1] < self.minIntensity:
                self.minIntensity = linearCameraData[i][1]
            self.avgIntensity += linearCameraData[i][1]
        
        # calculate average
        if len(linearCameraData) > 0:
            self.avgIntensity /= len(linearCameraData)
        else:
            self.avgIntensity = 0

        self.maxIntensity = peakLeft
        self.peakIntensity = (peakIleft + peakIright) / 2
    
        self.deltaIntensity = self.maxIntensity - self.minIntensity
        
        peak = PolyLine([(self.peakIntensity, 0), (self.peakIntensity, 255)], legend= 'Peak', colour='blue')
        graphs.append(peak)
        
        avg = PolyLine([(0, self.avgIntensity), (102, self.avgIntensity)], legend= 'Average', colour=wx.Color(0,127,0))
        # only add the average line if it's above zero
        if self.avgIntensity > 0:
            graphs.append(avg)
        
        # plot everything on a graph
        return PlotGraphics(graphs, "", "", "Intensity")
    
    def toggleConnect(self, event):
        global serialComm, endComm, linearCameraData
        if serialComm == 0:
            if self.deviceList.GetStringSelection() != '':
                # start serial
                try:
                    serialComm = serial.Serial(port=self.deviceList.GetStringSelection(), baudrate=9600, timeout=1, writeTimeout=1)
                except serial.SerialException:
                    wx.MessageBox('Could not connect to device', 'Error', wx.OK|wx.ICON_ERROR)
                    serialComm = 0
                    return
            
                # load integration time value (2 bytes) from device
                serialComm.write('c')
                it_high = serialComm.read(1)
                it_low = serialComm.read(1)
                if not it_high or not it_low:
                    wx.MessageBox('Check connection please', 'Error', wx.OK|wx.ICON_ERROR)
                    serialComm = 0
                    return
                
                self.tc_intTime.SetValue(str((ord(it_high) << 8) + ord(it_low)))
            
                # relabel button
                self.b_toggleConnect.SetLabel("Disconnect")
                
                self.lastGo = 0
                # enable controls
                self.b_setIntTime.Enable()
                self.b_forwards.Enable()
                self.b_back.Enable()
                self.b_left.Enable()
                self.b_right.Enable()
                self.b_stop.Enable()
                
                # start communication thread
                self.worker = commThread(self, 1)
                self.worker.start()
        else:
            # ask for serial communication end
            endComm = 1
    
    def scanDevices(self, event):
        # rescan available devices
        self.deviceList.Clear()
        self.getDevices()
        self.deviceList.AppendItems(self.devices)
    
    def setIntTime(self, event):
        global serialComm, commQueue
        if serialComm != 0:
        
            if not self.tc_intTime.GetValue().isdigit():
                wx.MessageBox('Integration time must be a positive numeric value', 'Error', wx.OK|wx.ICON_ERROR)
                return
            
            value = int(self.tc_intTime.GetValue())
            
            if value < 0 or value > 65535:
                wx.MessageBox('Integration time must be between 0 and 65535', 'Error', wx.OK|wx.ICON_ERROR)
                return
        
            # send new integration time to device one byte at a time
            commQueue.append('t' + chr(value >> 8) + chr(value & 0xff))
    
    def onKey(self, event):
        k = event.GetKeyCode()
        if k == 119 or k == wx.WXK_UP:
            self.go('forwards')
        elif k == 115 or k == wx.WXK_DOWN:
            self.go('back')
        elif k == 97 or k == wx.WXK_LEFT:
            self.go('left')
        elif k == 100 or k == wx.WXK_RIGHT:
            self.go('right')
        elif k == wx.WXK_SPACE:
            self.go('stop')
        else:
            event.Skip()

    def go(self, direction):
        global serialComm, commQueue
        # prevent sending commands when no connection is available or the last command was the same as the new
        if serialComm == 0 or self.lastGo == direction:
            return
        
        # verify user input value
        if not self.tc_speed.GetValue().isdigit():
            wx.MessageBox('Speed must be a positive numeric value', 'Error', wx.OK|wx.ICON_ERROR)
            return
            
        speed = int(self.tc_speed.GetValue())
        
        if speed < 1 or speed > 100:
            wx.MessageBox('Speed must be between 1 and 100', 'Error', wx.OK|wx.ICON_ERROR)
            return
        
        if direction == 'forwards':
            left = speed
            right = speed
        elif direction == 'back':
            left = -speed
            right = -speed
        elif direction == 'left':
            left = -speed
            right = speed
        elif direction == 'right':
            left = speed
            right = -speed
        else:
            left = 0
            right = 0
        
        # twos completent
        if left < 0:
            left = 256+left
        if right < 0:
            right = 256+right
        
        # send command to queue
        commQueue.append('s' + chr(left) + chr(right))
        self.lastGo = direction
    
    def resetGo(self, event):
        self.lastGo = 0
        
    def InitUI(self):
        # asynchronous ui update event
        self.Bind(wx.PyEventBinder(EVENT_UPDATE, 1), self.uiUpdate)
        self.Bind(wx.PyEventBinder(EVENT_RESET, 1), self.uiReset)
        self.Bind(wx.PyEventBinder(EVENT_DISCONNECTED, 1), self.uiReset)
        
        # keyboard shortcuts
        self.Bind(wx.EVT_CHAR_HOOK, self.onKey)
        
        # build the user interface
        
        # a vertical box sizer that lists items vertically
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vbox)
        self.SetMinSize((600,500));
        
        # main panel
        lc_pnl = wx.Panel(self)
        
        # containter box with label
        lc_sb = wx.StaticBox(lc_pnl, label='Linear Camera Output')
        # horizontal box to align the graph and controls
        lc_sbs = wx.StaticBoxSizer(lc_sb, orient=wx.HORIZONTAL)
        # size the panel according to the box sizer
        lc_pnl.SetSizer(lc_sbs)
        
        # create graph
        self.canvas = PlotCanvas(lc_pnl)
        self.canvas.Draw(self.drawLinearCameraOutput(), xAxis=(0,102), yAxis=(0,255))
        # add graph to horizontal static box sizer, with a proportion of 3 and fill the available space
        lc_sbs.Add(self.canvas, 3, wx.EXPAND)
        
        # linear camera control and values
        lc_bs_ctrl = wx.BoxSizer(wx.VERTICAL)
        lc_sbs.Add(lc_bs_ctrl, 1, wx.LEFT, 5)
        
        # intergration time label
        lc_bs_ctrl.Add(wx.StaticText(lc_pnl, label="Integration time [μs]"))
        
        # control interface elements
        self.tc_intTime = wx.TextCtrl(lc_pnl, style=wx.TE_PROCESS_ENTER)
        self.tc_intTime.Bind(wx.EVT_TEXT_ENTER, self.setIntTime)
        
        # button to send intergration time value to robot
        self.b_setIntTime = wx.Button(lc_pnl, label='Set')
        self.b_setIntTime.Bind(wx.EVT_BUTTON, self.setIntTime)
        
        # graph values
        self.st_peak = wx.StaticText(lc_pnl)
        self.st_peak.SetForegroundColour((0,0,255))
        self.st_max = wx.StaticText(lc_pnl)
        self.st_max.SetForegroundColour((255,0,0))
        self.st_min = wx.StaticText(lc_pnl)
        self.st_min.SetForegroundColour((255,0,0))
        self.st_delta = wx.StaticText(lc_pnl)
        self.st_delta.SetForegroundColour((255,127,0))
        self.st_avg = wx.StaticText(lc_pnl)
        self.st_avg.SetForegroundColour((0,127,0))
        
        # 3 rows, 2 columns, horizontal spacing = 5
        lc_gs = wx.GridSizer(3, 2, 0, 5)
        lc_bs_ctrl.Add(lc_gs, flag=wx.EXPAND)
        
        # arguments: item, proportion, fill available space flag
        lc_gs.AddMany([
            (self.tc_intTime, 1, wx.EXPAND),
            (self.b_setIntTime, 1, wx.EXPAND),
            (wx.StaticText(lc_pnl, label="Peak"), 1, wx.EXPAND),
            (self.st_peak, 1, wx.EXPAND),
            (wx.StaticText(lc_pnl, label="Maximum"), 1, wx.EXPAND),
            (self.st_max, 1, wx.EXPAND),
            (wx.StaticText(lc_pnl, label="Minimum"), 1, wx.EXPAND),
            (self.st_min, 1, wx.EXPAND),
            (wx.StaticText(lc_pnl, label="Delta"), 1, wx.EXPAND),
            (self.st_delta, 1, wx.EXPAND),
            (wx.StaticText(lc_pnl, label="Average"), 1, wx.EXPAND),
            (self.st_avg, 1, wx.EXPAND)
        ])
        
        # add the vertical box to the panel
        vbox.Add(lc_pnl, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
        
        # sensor values panel
        sv_pnl = wx.Panel(self)
        vbox.Add(sv_pnl, flag=wx.ALL|wx.EXPAND, border=5)
        sv_sb = wx.StaticBox(sv_pnl, label='IR Sensor Values')
        sv_sbs = wx.StaticBoxSizer(sv_sb, orient=wx.HORIZONTAL)
        sv_pnl.SetSizer(sv_sbs)
        
        # text fields for IR sensor values
        self.ir_0 = wx.TextCtrl(sv_pnl, style=wx.TE_READONLY)
        self.ir_1 = wx.TextCtrl(sv_pnl, style=wx.TE_READONLY)
        self.ir_2 = wx.TextCtrl(sv_pnl, style=wx.TE_READONLY)
        self.ir_3 = wx.TextCtrl(sv_pnl, style=wx.TE_READONLY)
        self.ir_4 = wx.TextCtrl(sv_pnl, style=wx.TE_READONLY)
        
        # show on user interface
        sv_sbs.Add(self.ir_0, 1, flag=wx.RIGHT, border=5)
        sv_sbs.Add(self.ir_1, 1, flag=wx.RIGHT, border=5)
        sv_sbs.Add(self.ir_2, 1, flag=wx.RIGHT, border=5)
        sv_sbs.Add(self.ir_3, 1, flag=wx.RIGHT, border=5)
        sv_sbs.Add(self.ir_4, 1)
        
        # align 2 panels horizontally
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox.Add(hbox, flag=wx.EXPAND)
        
        # connection interface panel
        ci_pnl = wx.Panel(self)
        hbox.Add(ci_pnl, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
        ci_sb = wx.StaticBox(ci_pnl, label='Connect')
        ci_sbs = wx.StaticBoxSizer(ci_sb, orient=wx.VERTICAL)
        ci_pnl.SetSizer(ci_sbs)
        
        # scan for the available USB connected devices
        self.getDevices()
        self.deviceList = wx.ListBox(ci_pnl, choices=self.devices, style=wx.CB_READONLY)
        ci_sbs.Add(self.deviceList, 1, wx.EXPAND)
        
        # connection interface buttons
        cib_bs = wx.BoxSizer(wx.HORIZONTAL)
        ci_sbs.Add(cib_bs, 0, wx.EXPAND)
        
        # toggle connection to serial device
        self.b_toggleConnect = wx.Button(ci_pnl, label='Connect')
        self.b_toggleConnect.Bind(wx.EVT_BUTTON, self.toggleConnect)
        cib_bs.Add(self.b_toggleConnect, 1, wx.TOP|wx.RIGHT|wx.EXPAND, 5)
        
        # refresh serial devices button
        self.b_refresh = wx.Button(ci_pnl, label='Refresh list')
        self.b_refresh.Bind(wx.EVT_BUTTON, self.scanDevices)
        cib_bs.Add(self.b_refresh, 1, wx.TOP|wx.EXPAND, 5)
        
        # movement control elements panel
        ce_pnl = wx.Panel(self)
        hbox.Add(ce_pnl, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
        ce_sb = wx.StaticBox(ce_pnl, label='Control')
        ce_sbs = wx.StaticBoxSizer(ce_sb, orient=wx.VERTICAL)
        ce_pnl.SetSizer(ce_sbs)
        
        # control button images
        img_forwards = wx.Image("images/forwards.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        img_left = wx.Image("images/left.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        img_back = wx.Image("images/back.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        img_right = wx.Image("images/right.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        img_stop = wx.Image("images/stop.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        
        # speed control box
        sc_bs = wx.BoxSizer(wx.VERTICAL)
        sc_bs.Add(wx.StaticText(ce_pnl, label="Speed [%]"))
        self.tc_speed = wx.TextCtrl(ce_pnl, value=str(self.speed))
        self.tc_speed.Bind(wx.EVT_TEXT, self.resetGo)
        sc_bs.Add(self.tc_speed, 0, wx.EXPAND)
        
        # control buttons
        self.b_forwards = wx.BitmapButton(ce_pnl, bitmap=img_forwards)
        self.b_forwards.Bind(wx.EVT_BUTTON, lambda event: self.go('forwards'))
        self.b_forwards.SetToolTip(wx.ToolTip("Forwards"))
        self.b_left = wx.BitmapButton(ce_pnl, bitmap=img_left)
        self.b_left.Bind(wx.EVT_BUTTON, lambda event: self.go('left'))
        self.b_left.SetToolTip(wx.ToolTip("Left"))
        self.b_back = wx.BitmapButton(ce_pnl, bitmap=img_back)
        self.b_back.Bind(wx.EVT_BUTTON, lambda event: self.go('back'))
        self.b_back.SetToolTip(wx.ToolTip("Back"))
        self.b_right = wx.BitmapButton(ce_pnl, bitmap=img_right)
        self.b_right.Bind(wx.EVT_BUTTON, lambda event: self.go('right'))
        self.b_right.SetToolTip(wx.ToolTip("Right"))
        self.b_stop = wx.BitmapButton(ce_pnl, bitmap=img_stop)
        self.b_stop.Bind(wx.EVT_BUTTON, lambda event: self.go('stop'))
        self.b_stop.SetToolTip(wx.ToolTip("Stop"))
        
        # add a grid with 2 rows and 3 colums with a vertical and horizontal spacing of 5
        ce_gs = wx.GridSizer(3, 3, 5, 5)
        ce_gs.AddMany([
            (0,0),
            (self.b_forwards, 1, wx.EXPAND),
            (sc_bs, 1, wx.EXPAND),
            (self.b_left, 1, wx.EXPAND),
            (self.b_stop, 1, wx.EXPAND),
            (self.b_right, 1, wx.EXPAND),
            (0,0),
            (self.b_back, 1, wx.EXPAND),
            (0,0)
        ])
        ce_sbs.Add(ce_gs, flag=wx.EXPAND)
        self.uiReset(0)

if __name__ == '__main__':
    app = wx.App()
    Control(None, title='')
    app.MainLoop()
