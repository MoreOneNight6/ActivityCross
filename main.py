#!/usr/bin/env python3
import os.path
import sys
import daemoniker
import wx
from wx.lib.newevent import NewEvent
import appdirs
from daemoniker import Daemonizer, SignalHandler1
from multiprocessing.connection import Listener
import json
import logging
import daemoner
import time
from settings import Settings,SETTINGS_FILE

###############
### LOGGING ###
###############

wxStdOut, EVT_STDDOUT = NewEvent()
# Logging handeler to gui
class GUILogger(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        #print(record)
        Msg = self.format(record).rstrip() + "\n"
        evt = wxStdOut(text=Msg, level=record.levelno)
        wx.PostEvent(wx.GetApp(), evt)
        #return super().emit(record)

Format = logging.Formatter('%(asctime)s %(levelname)-4s %(message)s\n')
#for GUILog in [logging.getLogger(name) for name in logging.root.manager.loggerDict]:
#for GUILog in [logging.getLogger(), logging.getLogger("daemoniker")]:
GUILog = logging.getLogger()
print(GUILog)
GUILogObj = GUILogger()
GUILoggerHandler = GUILogObj
GUILoggerHandler.setFormatter(Format)
GUILog.addHandler(GUILoggerHandler)
GUILog.setLevel(logging.INFO)

###########
### GUI ###
###########

# Logging and daemon control panel
# Refactor out logging portion
class DaemonPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.DaemonControlOn = False
        self.DaemonLogWindow = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.DaemonStartButton = wx.Button(self)
        self.DaemonStartButton.Bind(wx.EVT_BUTTON, self.DaemonToggle)

        self.PidText = wx.StaticText(self)
        #self.StatusText = wx.StaticText(self, label="Pending")
        self.StatusText = wx.StaticText(self, label="Pending")
        #self.NoDaemonizeCheck = wx.CheckBox(self, label="Bypass daemonization")

        Sizer1 = wx.BoxSizer(wx.VERTICAL)
        Sizer1.Add(self.DaemonLogWindow, 1, wx.ALL | wx.EXPAND, border=4)
        self.Sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.Sizer2.Add(self.DaemonStartButton)
        self.Sizer2.Add(self.PidText, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=8)
        self.Sizer2.Add(self.StatusText, 2, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=4)
        #self.Sizer2.Add(self.NoDaemonizeCheck, 0,  wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=4)
        Sizer1.Add(self.Sizer2, 0, wx.ALL | wx.EXPAND, border=4)

        self._DetermineDaemonState()

        self.SetSizer(Sizer1)
        Sizer1.Fit(self)
        #self.Bind(wx.EVT_SHOW, self._StartMonitoringProcess)

        self.MonoFont = wx.Font(70, wx.FONTFAMILY_TELETYPE, wx.NORMAL, wx.NORMAL, faceName="Monospace")
        self.DefaultAttr = wx.TextAttr(wx.NullColour, font= self.MonoFont)

        #self.control = wx.BoxSizer(wx.VERTICAL)
        #self.control.Add(self.DaemonLogWindow)

    def Write(self, e):
        self.DaemonLogWindow.SetDefaultStyle(self.DefaultAttr)
        if len(e.text) > 0:
            if hasattr(e, "level"):
                if e.level >= 40:
                    self.DaemonLogWindow.SetDefaultStyle(wx.TextAttr(wx.RED, font=self.MonoFont))
                elif e.level >= 30:
                    self.DaemonLogWindow.SetDefaultStyle(wx.TextAttr(wx.YELLOW, font=self.MonoFont))
                elif e.level > 0:
                    self.DaemonLogWindow.SetDefaultStyle(wx.TextAttr(wx.LIGHT_GREY, font=self.MonoFont))
            self.DaemonLogWindow.AppendText(e.text)

    def DaemonWrite(self,e):
        self.DaemonLogWindow.SetDefaultStyle(wx.TextAttr(wx.CYAN, font=self.MonoFont))
        self.DaemonLogWindow.AppendText(e.text)

    def DaemonToggle(self, e):
        self.DaemonStartButton.Disable()
        if daemoner.GetDaemonProcess():
            daemoner.StopDaemon()
            if daemoner.GetDaemonProcess():
                logging.error("Failed to stop daemon")
                self.DaemonStartButton.SetLabel("Failed to stop")
            else:
                self._DetermineDaemonState()
        else:
            daemoner.StartDaemon(Settings()["RunAsDaemon"])
            if not daemoner.GetDaemonProcess():
                logging.error("Failed to start daemon")
                self.DaemonStartButton.SetLabel("Failed to start")
            else:
                self._DetermineDaemonState()
        self.DaemonStartButton.Enable()

    def _DetermineDaemonState(self):
        Process = daemoner.GetDaemonProcess()
        if Process:
            self.DaemonStartButton.SetLabel("Stop Daemon")
            #self.CurrentText.SetLabel("Daemon Stopped")
            #self.Layout()
            self.StatusText.SetLabel("Deamon active")
            self.StatusText.SetForegroundColour((0,255,0))
            self.PidText.SetLabel(f"PID {Process.pid}")
        else:
            self.DaemonStartButton.SetLabel("Start Daemon")
            #self.CurrentText.SetLabel("Daemon Started")
            #self.Layout()
            #self.PidText.SetLabel("")
            #print(DaemonState)
            self.StatusText.SetLabel("Deamon inactive")
            self.StatusText.SetForegroundColour((255,0,0))
            self.PidText.SetLabel("PID ??????")
            #self.PidText.Hide()

        self.Sizer2.Layout()



class SettingsPanel(wx.Panel):
    #_Settings = {
    #    "RunAsDaemon":"Run as daemon",
    #    #"WaitTime":"Wait Time",
    #    "AFKTime":"AFK Time",
    #    "PidPath":"Pid Path",
    #}

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        Sizer1 = wx.BoxSizer(wx.VERTICAL)
        self.ScrolledPanel = wx.ScrolledWindow(self, style=wx.VSCROLL)
        ScrolledPanelSizer = wx.BoxSizer(wx.VERTICAL)

        # General Settings
        self.GenSizer = wx.StaticBoxSizer(wx.VERTICAL, self, label="General Settings")
        RunAsDaemonCheck = wx.CheckBox(self.ScrolledPanel, label="Run watcher as daemon?")
        RunAsDaemonCheck.SetValue(Settings()["RunAsDaemon"])
        def _RunAsDaemonCheck(e):
            logging.info("Set RunAsDaemon to %s", RunAsDaemonCheck.Value)
            Settings()["RunAsDaemon"] = RunAsDaemonCheck.Value
            print(Settings()["RunAsDaemon"])
        RunAsDaemonCheck.Bind(wx.EVT_CHECKBOX, _RunAsDaemonCheck)
        self.GenSizer.Add(RunAsDaemonCheck)

        # Bottom Bar
        DiskIcon = wx.ArtProvider().GetBitmapBundle(wx.ART_FILE_SAVE, client=wx.ART_BUTTON)
        ApplyButton = wx.Button(self, label="Save to disk")
        ApplyButton.SetBitmap(DiskIcon)
        def _ApplyButtonSave(e):
            Setting = Settings()
            Setting.Save()
            #Setting.store = Setting.Read()
        ApplyButton.Bind(wx.EVT_BUTTON, _ApplyButtonSave)

        SizerBottom = wx.BoxSizer(wx.HORIZONTAL)
        SizerBottom.Add(ApplyButton)
        SizerBottom.Add(wx.StaticText(self, label=SETTINGS_FILE), 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=8)
        ScrolledPanelSizer.Add(self.GenSizer, 1, wx.ALL | wx.EXPAND, border=4)

        self.ScrolledPanel.SetSizer(ScrolledPanelSizer)
        ScrolledPanelSizer.Fit(self.ScrolledPanel)
        Sizer1.Add(self.ScrolledPanel, 1, wx.ALL | wx.EXPAND)
        Sizer1.Add(SizerBottom, 0, wx.ALL | wx.EXPAND, border=4)
        self.SetSizer(Sizer1)
        Sizer1.Fit(self)

class MainWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="ActivityCross", size=(600,400))
        self.CreateStatusBar() # A StatusBar in the bottom of the window

        # Setting up the menu.
        filemenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard ids provided by wxWidgets.
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # Set events.
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

        Tabs = wx.Notebook(self)
        # Daemon Panel
        self.DaemonPanelObj = DaemonPanel(Tabs)
        self.SettingPanelObj = SettingsPanel(Tabs)

        # Create tabs
        control = wx.TextCtrl(Tabs, style=wx.TE_MULTILINE)
        control2 = wx.TextCtrl(Tabs, style=wx.TE_MULTILINE)
        control3 = wx.TextCtrl(Tabs, style=wx.TE_MULTILINE)
        Tabs.AddPage(control, "Overview")
        Tabs.AddPage(control3, "Timeline")
        Tabs.AddPage(self.SettingPanelObj, "Settings")
        Tabs.AddPage(self.DaemonPanelObj, "Daemon")
        Tabs.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNotebookUpdated)
        self.control = Tabs

    # Menu callbacks
    def OnAbout(self,e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog( self, "A small text editor", "About Sample Editor", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.

    def OnExit(self,e):
        self.Close(True)

    def OnNotebookUpdated(self, event):
        pass
        #Num = event.GetSelection()
        #if Num == 3:
        #    self.DaemonPanelObj._StartMonitoringProcess()
        #else:
        #    self.DaemonPanelObj._StopMonitoringProcess()

    # Write sysout to DaemonPanel log
    #def OnUpdateOutputWindow(self, event):
    #    value = event.text
    #    self.output_window.AppendText(value)

def Main():
    app = wx.App()
    frame = MainWindow(None)
    app.Bind(EVT_STDDOUT, frame.DaemonPanelObj.Write)
    frame.Show(True)
    app.MainLoop()
print(__name__)
if __name__ == "__main__":
    Main()
