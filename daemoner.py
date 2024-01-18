import os.path
import wx
import wx.lib.newevent
import psutil
from daemoniker import Daemonizer, SignalHandler1
import daemoniker
import multiprocessing
import json
import time
import logging
import platform
import datetime
from settings import Settings
import settings
import threading
#from dataclasses_json import dataclass_json

PID_FILE = "pid"

##############
### DAEMON ###
##############

# https://stackoverflow.com/questions/2697039/python-equivalent-of-setinterval
# Used in _DaemonFunc to schedule when to set AFK
class SetInterval():
    def __init__(self,interval,action) :
        self.interval=interval
        self.action=action
        self.stopEvent=threading.Event()
        thread=threading.Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self) :
        nextTime=time.time()+self.interval
        while not self.stopEvent.wait(nextTime-time.time()) :
            nextTime+=self.interval
            self.action()
        else:
            self.stopEvent.clear()

    def Pause(self, *args) :
        self.stopEvent.set()


# Code to be run in daemon process
LastWindow = (None, None)
def _DaemonFunc(PID_FILE, Daemonize, DATA_FILE, AFKTime):
    if Daemonize:
        with Daemonizer() as (is_setup, daemonizer):
            sighandler = SignalHandler1(PID_FILE)
            sighandler.start()
            is_parent = daemonizer(PID_FILE)
    time.sleep(0.5)


    Sniffer = None
    if platform.system() == "Linux":
        from sniff_x import Sniffer
    if Sniffer == None:
        return

    def WriteAFK():
        print("AFK")

    def WriteWindow(Class, Title, *args):
        # TODO: Remove this once i fix bounding erorr
        global LastWindow
        if LastWindow[0] != Class or LastWindow[1] != Title:
            print("NYAA", Class, Title)
            #DataFileObj.WriteCurrent((Class, Title))
            #WriteCurrent((Class, Title))
            LastWindow = (Class, Title)

    Timer = SetInterval(AFKTime, WriteAFK)
    Sniffy = Sniffer()
    Sniffy.key_hook = Timer.Pause
    Sniffy.mouse_button_hook = Timer.Pause
    Sniffy.mouse_move_hook = Timer.Pause
    Sniffy.screen_hook = WriteWindow

    #snapshot = tracemalloc.take_snapshot()
    #top_stats = snapshot.statistics('lineno')

    #print("[ Top 30 ]")
    #for stat in top_stats[:30]:
    #    print(stat)


    Sniffy.run()

######################
### DAEMON CONTROL ###
######################

def GetDaemonProcess():
    PID_DIR = os.path.dirname(PID_FILE)
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as Fp:
                PIDText = Fp.read()
                if PIDText != "":
                    PID = int(PIDText)
                    return psutil.Process(PID)
        except psutil.NoSuchProcess:
            return None
        except Exception as E:
            logging.warning(str(E))
    elif PID_DIR != "" and not os.path.exists(PID_DIR):
        logging.warn("Could not find PID_FILE directory %s", PID_DIR)
        logging.warn("Recusrively creating")
        os.makedirs(PID_DIR)
    return None

# Stops process
def StopDaemon():
    logging.info("--- Stopping daemon ---")
    logging.info("Daemon is running")
    try:
        daemoniker.send(PID_FILE, daemoniker.SIGINT)
        logging.info("Removing stray PID file")
        os.remove(PID_FILE)
    except ProcessLookupError:
        logging.warning("Process does not exist, already stopped")
    except Exception as E:
        logging.error(str(E))
    logging.info("Finished stopping process")
    logging.info("-----------------------")

# Starts process
def StartDaemon(Daemonize=True):
    try:
        if GetDaemonProcess() == None and os.path.exists(PID_FILE):
            logging.warning("Pid file exists eventhough no process")
            os.remove(PID_FILE)
        def WaitFor(Func):
            Num = 0
            while Func():
                logging.info("(%s) Waiting for process to appear...", Num)
                for i in range(5):
                    time.sleep(0.02)
                    wx.Yield()
                if Num == 100:
                    logging.warning("Timed out")
                    break
                Num += 1
        logging.info("--- Starting daemon ---")
        p = multiprocessing.Process(target=_DaemonFunc, args=(PID_FILE,Settings()["RunAsDaemon"], Settings()["DataPath"], Settings()["AFKTime"]))
        p.start()
        logging.info("Launched monitoring daemon")
        if Daemonize:
            logging.info("Waiting for daemonized process")
            WaitFor(lambda : GetDaemonProcess() == None)
            p.join()
        else:
            logging.info("Waiting for regular process")
            WaitFor(lambda : p.pid == None)
            with open(PID_FILE, "w") as Fp:
                Fp.write(str(p.pid))
    except Exception as E:
        logging.error(str(E))
    logging.info("Finished starting process")
    logging.info("------------------------")
