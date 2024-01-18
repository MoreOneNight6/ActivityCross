#import datetime
import json
import logging
#import multiprocessing
import os
#from queue import Queue
#import queue
#from dataclasses import dataclass
#from dataclasses_json import dataclass_json
#from dataclasses_json import DataClassJsonMixin
#import wx.lib.newevent
import wx
from collections.abc import MutableMapping

#from watchdog.observers import Observer
#from watchdog.observers.api import ObservedWatch

APP_NAME="ActivityCross"
APP_AUTHOR="juser"
APP_VER=1.0
try:
    import appdirs
    SETTINGS_FILE=os.path.join(appdirs.user_config_dir(APP_NAME, APP_AUTHOR), "config.json")
    DATA_DIR = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
except ImportError:
    SETTINGS_FILE="settings.json"
    DATA_DIR = ""
    logging.warning("Couldnt get platform native config path")
SETTINGS_DIR = os.path.dirname(SETTINGS_FILE)

class Singleton(object):
    _instance = None
    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            if "__post_init__" in class_.__dict__:
                class_._instance.__post_init__()
        return class_._instance

class Settings(Singleton, MutableMapping):
    #RunAsDaemon: bool = True
    #PidPath: str = "pid"
    #AFKTime: int = 120
    #DataPath: str = os.path.join(DATA_DIR)

    #def __init__(self):
    #    self.Read()
        #self.store = self.Read()

    def __post_init__(self):
        self.Read()

    def Read(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as Fp:
                pass
                #self.InternalDict = json.load(Fp)
                logging.info("Loaded config file from directory")
                self.store = json.load(Fp)
        else:
            logging.info("Config file could not be found")
            self.store = {
                "RunAsDaemon": True,
                "PidPath": "pid",
                "AFKTime": 120,
                "DataPath": DATA_DIR
            }

    def Save(self):
        if not os.path.exists(SETTINGS_DIR) and SETTINGS_DIR != "":
            os.makedirs(SETTINGS_DIR)
        with open(SETTINGS_FILE, "w") as Fp:
            logging.info("Saving settings file to "+ SETTINGS_FILE)
            json.dump(self.store, Fp)
            #json.dump(self.InternalDict, Fp)

    def __getitem__(self, key):
        return self.store[self._keytransform(key)]

    def __setitem__(self, key, value):
        self.store[self._keytransform(key)] = value

    def __delitem__(self, key):
        del self.store[self._keytransform(key)]

    def __iter__(self):
        return iter(self.store)
    
    def __len__(self):
        return len(self.store)

    def _keytransform(self, key):
        return key
#Settings()
#Settings()["_test"] = "r"
#print(Settings()["RunAsDaemon"])
#Settings = _Settings()
#Settings.Read()
