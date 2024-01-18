from functools import cache
from typing import Iterable, Tuple
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
import time
from enum import Enum

# A generator that returns the lines of a file in reverse order"""
#def reverse_readline(filename, buf_size=8192):
#    with open(filename, 'rb') as fh:
#        segment = None
#        offset = 0
#        fh.seek(0, os.SEEK_END)
#        file_size = remaining_size = fh.tell()
#        while remaining_size > 0:
#            offset = min(file_size, offset + buf_size)
#            fh.seek(file_size - offset)
#            buffer = fh.read(min(remaining_size, buf_size))
#            # remove file's last "\n" if it exists, only for the first buffer
#            if remaining_size == file_size and buffer[-1] == ord('\n'):
#                buffer = buffer[:-1]
#            remaining_size -= buf_size
#            lines = buffer.split('\n'.encode())
#            # append last chunk's segment to this chunk's last line
#            if segment is not None:
#                lines[-1] += segment
#            segment = lines[0]
#            lines = lines[1:]
#            # yield lines in this chunk except the segment
#            for line in reversed(lines):
#                # only decode on a parsed line, to avoid utf-8 decode error
#                yield line.decode()
#        # Don't yield None if the file was empty
#        if segment is not None:
#            yield segment.decode()


class Database():
    def __init__(self, DatabasePath):
        self.DatabasePath = DatabasePath

    def __enter__(self):
        Created = os.path.exists(self.DatabasePath)
        self.con = sqlite3.connect(self.DatabasePath)
        #self.FirstEvent = None
        #self.cur = self.con.cursor()
        if not Created:
            self.con.execute(Events.Event.Table)
            self.con.execute(Categories.Category.Table)
            logging.warning("Creating new database at %s", self.DatabasePath)
            #print("UWWWWW")
        return self

    def __exit__(self, *args):
        self.con.close()

# Class to handle categories for window
class Categories():

    # Data struct for one category
    @dataclass
    class Category():
        Table = """
        CREATE TABLE Categories (
            Name TEXT PRIMARY KEY,
            Parent TEXT,
            MatchingMode INT,
            MatchingTarget INT,
            Pattern TEXT,
            ColorR INT,
            ColorG INT,
            ColorB INT,
        )
        """
        class EMatchingMode(Enum):
            ALWAYS = 0
            PREFIX = 1
            EXACT  = 2
            REGEX  = 3

        class EMatchingTarget(Enum):
            TIMESTAMP = 0
            CLASS = 1
            NAME = 2
        Name: str
        MatchingMode: int
        MatchingTarget: int
        Pattern: str
        Color: tuple[int,int,int]
        Parent: str

        @staticmethod
        def FromTuple(SQLTuple):
            return Categories.Category(*SQLTuple[0:4])

        def ToTuple(self):
            return [self.Name, self.MatchingMode, self.MatchingTarget, self.Pattern, *self.Color[0:2]]


    def __init__(self, Con):
        self.Con = Con

    #def AddCategory(self, Category: Category):
    #    self.
        


# Class to handle window change events
class Events():
    # Data struct for one window event
    @dataclass()
    class Event():
        Table = """
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

    SQLToRecord = lambda x: [Events.Event(datetime.datetime.fromtimestamp(i[0]), i[1], i[2]) for i in x]
    
    def __init__(self, Con) -> None:
        #self.DatabasePath = DatabasePath
        self.con = Con
   
    @cache
    def _GetFirstEvent(self):
        Res = self.con.execute("SELECT * FROM Events ORDER BY ROWID ASC LIMIT 1")
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
        Res = self.con.execute("SELECT * FROM Events WHERE Timestamp < ? AND Timestamp > ? ORDER BY Timestamp", (Start.timestamp(), Stop.timestamp()))
        #Res = self.con.execute("SELECT * FROM Events")
        ResL = Res.fetchall()
        #print(ResL)
        if ResL != None:
            return [Events.Event.FromSQL(i) for i in Events.SQLToRecord(ResL)]

    def AddRecord(self, Record:Event) -> None:
        self.con.execute("INSERT INTO Events VALUES (?,?,?)", (Record.Timestamp.timestamp(), Record.Class, Record.Name))
        self.con.commit()

