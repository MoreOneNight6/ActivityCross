from functools import cache
#from ty
#import watchdog
#import watchdog.events
#import watchdog.observers
from dataclasses import dataclass
#from settings import DATA_DIR
#import wx.lib.newevent
import os
import datetime
import sqlite3
import logging
#import time
from enum import Enum
from typing import Optional
from closure_table import ClosureTable
import random

class Database():
    def __init__(self, DatabasePath):
        self.DatabasePath = DatabasePath

    def __enter__(self):
        Created = os.path.exists(self.DatabasePath)
        self.con = sqlite3.connect(self.DatabasePath)
        #self.FirstEvent = None
        #self.cur = self.con.cursor()
        if not Created:
            self.con.executescript(ClosureTable._Table)
            self.con.execute(Categories.Category._Table)
            logging.warning("Creating new database at %s", self.DatabasePath)
            #print("UWWWWW")
        return self.con

    def __exit__(self, *args):
        self.con.close()

################
### CATEGORY ###
################

class EMatchingMode(Enum):
    ALWAYS = 0
    PREFIX = 1
    EXACT  = 2
    REGEX  = 3

class EMatchingTarget(Enum):
    TIMESTAMP = 0
    CLASS = 1
    TITLE = 2
    CLASS_TITLE = 3

class Categories(ClosureTable):
    def __init__(self, conn):
        print(conn)
        super().__init__(conn)
        self.con = conn


    # Data struct for one category
    @dataclass
    class Category():
        _Table = """
        CREATE TABLE Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT,
            MatchingMode INT,
            MatchingTarget INT,
            Pattern TEXT,
            ColorR INT,
            ColorG INT,
            ColorB INT,
            Lowercase BOOL
            --FOREIGN KEY (CatID) REFERENCES data_table(id)
        )
        """
        Name: str
        MatchingMode: EMatchingMode
        MatchingTarget: EMatchingTarget
        Pattern: str
        _Color: tuple[int,int,int] = (100,100,100)
        #_CatID: int = int(random.random() * 1000000)
        _Lowercase: int = 0
        _CatID: Optional[int] = None

        @staticmethod
        def FromTuple(SQLTuple):
            return Categories.Category(SQLTuple[1],
                                       SQLTuple[2],
                                       SQLTuple[3],
                                       SQLTuple[4],
                                       (SQLTuple[5], SQLTuple[6], SQLTuple[7]),
                                       SQLTuple[8],
                                       SQLTuple[0])

        def ToTuple(self):
            return [self._CatID, 
                    self.Name, 
                    self.MatchingMode.value, 
                    self.MatchingTarget.value, 
                    self.Pattern, 
                    *self._Color,
                    self._Lowercase]

    def _InsertIntoSQL(self, Child:Category):
        Cur = self.con.cursor()
        FieldList = "Name, MatchingMode, MatchingTarget, Pattern, ColorR, ColorG, ColorB, Lowercase"
        if Child._CatID == None:
            print(Child.ToTuple()[1::], len(Child.ToTuple()[1::]))
            Cur.execute("""INSERT INTO Categories """ + 
                        " (" + FieldList + ") " +
                        """VALUES (?,?,?,?,?,?,?,?)""", Child.ToTuple()[1::])
        else:
            print(Child.ToTuple())
            Cur.execute("""INSERT INTO Categories """ +
                        " (" + "id,"+FieldList + ") " +
                        """VALUES (?,?,?,?,?,?,?,?,?)""", Child.ToTuple())
        ID = Cur.lastrowid
        Cur.close()
        Child._CatID = ID

    def GetRootNode(self):
        Root = self.select_children(0)
        if Root == []:
            print("CREATED")
            RootNode = Categories.Category("Undefined", 
                                           EMatchingMode.ALWAYS, 
                                           EMatchingTarget.TIMESTAMP,
                                           "")
            RootNode._CatID = 0
            self.insert_child(RootNode._CatID, RootNode._CatID)
            self._InsertIntoSQL(RootNode)
            self.con.commit()
            return RootNode
        else:
            print("LOADED", Root)
            return Categories.Category.FromTuple(Root[0])

    def NewCategory(self, Parent:Category, Child:Category):
        #Con.execute("INSERT INTO CatClosures
        self._InsertIntoSQL(Child)
        print(Child._CatID)
        self.insert_child(Parent._CatID, Child._CatID)
        self.con.commit()

#############
### EVENT ###
#############

class Events():

    def __init__(self, con):
        self.con = con

    # Data struct for one window event
    @dataclass()
    class Event():
        _Table = """
        CREATE TABLE Events (
            Timestamp REAL NOT NULL,
            Class TEXT,
            Name TEXT
        )"""

        Timestamp:datetime.datetime
        Class: str
        Name: str

        @staticmethod
        def FromSQL(SQLTuple):
            return Events.Event(SQLTuple[0], SQLTuple[1], SQLTuple[2])

        def ToSQL(self):
            return [self.Timestamp.timestamp(), self.Class, self.Name]

    @cache
    def _GetFirstEvent(self):
        con = self.con
        Res = con.execute("SELECT * FROM Events ORDER BY ROWID ASC LIMIT 1")
        Ret = Res.fetchone()
        logging.info("Finding DB first record")
        if Ret != None:
            Ret = Events.Event.FromSQL(Ret[0])
        else:
            logging.warning("Could not find database first event, timeline may be broken")
        #self.FirstEvent = Ret
        #print(Ret)
        return Ret

    def GetRange(self, Start: datetime.datetime, Stop:datetime.datetime):
        con=self.con
        Res = con.execute("SELECT * FROM Events WHERE Timestamp < ? AND Timestamp > ? ORDER BY Timestamp", (Start.timestamp(), Stop.timestamp()))
        #Res = self.con.execute("SELECT * FROM Events")
        ResL = Res.fetchall()
        #print(ResL)
        if ResL != None:
            return [Events.Event.FromSQL(i) for i in ResL]

    def AddRecord(self,Record:Event) -> None:
        con = self.con
        con.execute("INSERT INTO Events VALUES (?,?,?)", (Record.Timestamp.timestamp(), Record.Class, Record.Name))
        con.commit()


with Database("TestDB.db") as Conn:
    CatObj = Categories(Conn)
    GameObj = Categories.Category("Games", 
                                  EMatchingMode.REGEX, 
                                  EMatchingTarget.CLASS_TITLE,
                                  "Factorio")

    LewdGameObj = Categories.Category("Lewd Games", 
                                      EMatchingMode.REGEX, 
                                      EMatchingTarget.CLASS_TITLE,
                                      "Degrees Of Lewdity")
    LewdGameObj._Color = (255,0,0)

    CatObj.NewCategory(CatObj.GetRootNode(), GameObj)
    CatObj.NewCategory(GameObj, LewdGameObj)
    #print(Categories.GetRootNode())
