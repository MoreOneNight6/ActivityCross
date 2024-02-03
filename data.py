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

# How to match an event for Category
class EMatchingMode(Enum):
    ALWAYS = 0
    PREFIX = 1
    EXACT  = 2
    REGEX  = 3

# What to match event on for Category
class EMatchingTarget(Enum):
    TIMESTAMP = 0
    CLASS = 1
    TITLE = 2
    CLASS_TITLE = 3

# Wrapper for Category for interacting with database
# Uses closure table to represent hiearchy
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
            Lowercase BOOL,
            AlwaysActive BOOL
            --FOREIGN KEY (CatID) REFERENCES data_table(id)
        )
        """
        Name: str
        MatchingMode: EMatchingMode
        MatchingTarget: EMatchingTarget
        Pattern: str
        _Color: tuple[int,int,int] = (100,100,100)
        _Lowercase: int = 0
        _AlwaysActive: int = 0

        #_CatID: int = int(random.random() * 1000000)
        _Depth: Optional[int] = None
        _CatID: Optional[int] = None

        @staticmethod
        def FromTuple(SQLTuple):
            return Categories.Category(SQLTuple[1],
                                       SQLTuple[2],
                                       SQLTuple[3],
                                       SQLTuple[4],
                                       (SQLTuple[5], SQLTuple[6], SQLTuple[7]),
                                       SQLTuple[8],
                                       SQLTuple[9],
                                       SQLTuple[10],
                                       SQLTuple[0])

        def ToTuple(self):
            return [self._CatID, 
                    self.Name, 
                    self.MatchingMode.value, 
                    self.MatchingTarget.value, 
                    self.Pattern, 
                    *self._Color,
                    self._Lowercase,
                    self._AlwaysActive]

    def _InsertIntoSQL(self, Child:Category):
        Cur = self.con.cursor()
        FieldList = "Name, MatchingMode, MatchingTarget, Pattern, ColorR, ColorG, ColorB, Lowercase, AlwaysActive"
        if Child._CatID == None:
            print(Child.ToTuple()[1::], len(Child.ToTuple()[1::]))
            Cur.execute("""INSERT INTO Categories """ + 
                        " (" + FieldList + ") " +
                        """VALUES (?,?,?,?,?,?,?,?,?)""", Child.ToTuple()[1::])
        else:
            print(Child.ToTuple())
            Cur.execute("""INSERT INTO Categories """ +
                        " (" + "id,"+FieldList + ") " +
                        """VALUES (?,?,?,?,?,?,?,?,?,?)""", Child.ToTuple())
        ID = Cur.lastrowid
        Cur.close()
        Child._CatID = ID

    #def _DeleteFromSQL(self, Child:Category):
    #    self.con.execute("DELETE FROM Categories WHERE id = ?", (Child._CatID,))

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

    def AddCategory(self, Parent:Category, Child:Category):
        #Con.execute("INSERT INTO CatClosures
        self._InsertIntoSQL(Child)
        print(Child._CatID)
        self.insert_child(Parent._CatID, Child._CatID)
        self.con.commit()

    # TODO: Refactor these asserts with something more useful
    # These Get* Functions need Parent to be gotten from other Get* Functions
    # Or the objects been passed to AddCategory which mutates the object with an ID
    def GetChildren(self, Parent:Category):
        assert Parent._CatID != None
        Root = self.select_children(Parent._CatID)
        for i in Root:
            yield Categories.Category.FromTuple(i)

    def GetSubtree(self, Parent:Category):
        assert Parent._CatID != None
        Root = self.select_descendants(Parent._CatID)
        for i in Root:
            yield (Categories.Category.FromTuple(i), self.descendants_depth(i[0])-1)

    def DeleteSubtree(self, Parent:Category):
        assert Parent._CatID != None
        # TODO: Refactor this to use SQL native commands
        for k in [Parent, *[i[0] for i in self.GetSubtree(Parent)]]:
            print("TO BE DLETED", k, k._CatID)
            self.con.execute("DELETE FROM Categories WHERE id = ?", (k._CatID,))
        self.delete_descendants(Parent._CatID)
        self.con.commit()

#############
### EVENT ###
#############

# Wrapper for Event to interact with database
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


#with Database("TestDB.db") as Conn:
#    CatObj = Categories(Conn)
#    GameObj = Categories.Category("Movies2", 
#                                  EMatchingMode.REGEX, 
#                                  EMatchingTarget.CLASS_TITLE,
#                                  "mpv")
#    TestGameObj = Categories.Category("Web Video2", 
#                                      EMatchingMode.REGEX, 
#                                      EMatchingTarget.CLASS_TITLE,
#                                      "youtube")
#    TestGameObj._Color = (255,0,0)
#    Root = CatObj.GetRootNode()
#    CatObj.AddCategory(Root, GameObj)
#    CatObj.AddCategory(GameObj, TestGameObj)
#
#
#    CatObj.DeleteSubtree(TestGameObj)
#    for i in CatObj.GetSubtree(Root):
#        print(i)
