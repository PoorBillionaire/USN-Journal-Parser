#!/usr/bin/python

# Copyright 2015 Adam Witt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from argparse import ArgumentParser
import collections
from datetime import datetime,timedelta
import json
import os
import struct
import sys


usnReasons = collections.OrderedDict(
              {
               0x1 : "DATA_OVERWRITE",
               0x2 : "DATA_EXTEND",
               0x4 : "DATA_TRUNCATION",
               0x10 : "NAMED_DATA_OVERWRITE",
               0x20 : "NAMED_DATA_EXTEND",
               0x40 : "NAMED_DATA_TRUNCATION",
               0x100 : "FILE_CREATE",
               0x200 : "FILE_DELETE",
               0x400 : "EA_CHANGE",
               0x800 : "SECURITY_CHANGE",
               0x1000 : "RENAME_OLD_NAME",
               0x2000 : "RENAME_NEW_NAME",
               0x4000 : "INDEXABLE_CHANGE",
               0x8000 : "BASIC_INFO_CHANGE",
               0x10000 : "HARD_LINK_CHANGE",
               0x20000 : "COMPRESSION_CHANGE",
               0x40000 : "ENCRYPTION_CHANGE",
               0x80000 : "OBJECT_ID_CHANGE",
               0x100000 : "REPARSE_POINT_CHANGE",
               0x200000 : "STREAM_CHANGE",
               0x80000000 : "CLOSE"
              }
)

fileAttributes = collections.OrderedDict(
                  {
                   0x1 : "READONLY",
                   0x2 : "HIDDEN",
                   0x4 : "SYSTEM",
                   0x10 : "DIRECTORY",
                   0x20 : "ARCHIVE",
                   0x40 : "DEVICE",
                   0x80 : "NORMAL",
                   0x100 : "TEMPORARY",
                   0x200 : "SPARSE_FILE",
                   0x400 : "REPARSE_POINT",
                   0x800 : "COMPRESSED",
                   0x1000 : "OFFLINE",
                   0x2000 : "NOT_CONTENT_INDEXED",
                   0x4000 : "ENCRYPTED",
                   0x8000 : "INTEGRITY_STREAM",
                   0x10000 : "VIRTUAL",
                   0x20000 : "NO_SCRUB_DATA"
                  }
)


def convert_word(twobytes):
    return struct.unpack_from("H", twobytes)[0]

def convert_dword(fourbytes):
    return struct.unpack_from("I", fourbytes)[0]

def convert_dwordlong(eightbytes):
    return struct.unpack_from("Q", eightbytes)[0]

def convert_double_dwordlong(sixteenbytes):
    return struct.unpack_from("2Q", sixteenbytes)[0]


def findFirstRecord(infile):
    # Returns a pointer to the first USN record found
    # Modified version of Dave Lassalle's "parseusn.py"
    # https://github.com/sans-dfir/sift-files/blob/master/scripts/parseusn.py

    while True:
        data = infile.read(6553600)
        data = data.lstrip('\x00')
        if data:
            infile.seek(infile.tell() - len(data))
            break


def findFirstRecordQuick(infile, filesize):
    # Same as findData(), but initially reads larger swaths of leading
    # NULL bytes to speed the time it takes to parse a larger journal file

    while True:
        if infile.tell() + 1073741824 < filesize:
            infile.seek(1073741824, 1)
            data = infile.read(6553600)
            data = data.lstrip("\x00")

            if data:
                infile.seek((-1073741824 + 6553600), 1)
                return findFirstRecord(infile)
        else:
            return findFirstRecord(infile)


def findNextRecord(infile, fileSize):
    # This function determines the recordlength of a USN record by
    # interpreting its first four bytes. This value is returned.
    #
    # Using the recordlength, it then calculates the start of the next
    # valid USN record. This value is also returned

    try:
        while True:
            recordlen = struct.unpack_from("I", infile.read(4))[0]
            if recordlen:
                infile.seek(-4, 1)
                return (infile.tell() + recordlen)
    except struct.error:
            if infile.tell() >= fileSize:
                sys.exit()


def convertTimestamp(timestamp):
    # The USN record's "timestamp" property is a Win32 FILETIME value
    # This function returns that value in a human-readable format
    return str(datetime(1601,1,1) + timedelta(microseconds=timestamp / 10.))


def convertReason(reason):
    # Returns the USN "reason" property in a human-readable format

    reasons = ""

    for item in usnReasons:
        if item & reason:
            reasons += usnReasons[item] + " "

    return reasons


def convertAttributes(fileattrs):
    # Returns the USN 'file attributes' property in a human-readable format

    attrlist = ""
    for item in fileAttributes:
        if fileattrs & item:
            attrlist += fileAttributes[item] + " "

    return attrlist


def daysago(n):
    # Return a list of dates between today and n days ago
    
    dates = []
    counter = 0

    while counter < int(n):
        date = str(datetime.now() - timedelta(days=counter))
        dates.append(date[0:10])
        counter += 1
    
    return dates

def prettyPrint(usn):
    record = {
              "recordlen" : usn.recordLength,
              "majversion" : usn.majorVersion,
              "minversion" : usn.minorVersion,
              "fileref" : usn.fileReferenceNumber,
              "parentfileref" : usn.pFileReferenceNumber,
              "usn" : usn.usn,
              "timestamp" : usn.timestamp,
              "reason" : usn.reason,
              "sourceinfo" : usn.sourceInfo,
              "sid" : usn.securityId,
              "fileattr" : usn.fileAttributes,
              "filenamelen" : usn.fileNameLength,
              "filenameoffset" : usn.fileNameOffset,
              "filename" : usn.filename
    }

    print json.dumps(record, indent=4)

class ParseUsn(object):
    def __init__(self, infile):
        self.recordLength(infile)
        self.majorVersion(infile)
        self.minorVersion(infile)
        self.fileReferenceNumber(infile)
        self.pFileReferenceNumber(infile)
        self.usn(infile)
        self.timestamp(infile)
        self.reason(infile)
        self.sourceInfo(infile)
        self.securityId(infile)
        self.fileAttributes(infile)
        self.fileNameLength(infile)
        self.fileNameOffset(infile)
        self.filename(infile)

    def recordLength(self, infile):
        self.recordLength = convert_dword(infile.read(4))

    def majorVersion(self, infile):
        self.majorVersion = convert_word(infile.read(2))
    
    def minorVersion(self, infile):
        self.minorVersion = convert_word(infile.read(2))

    def fileReferenceNumber(self, infile):
        if self.majorVersion == 2:
            self.fileReferenceNumber = convert_dwordlong(infile.read(8))
        elif self.majorVersion == 3:
            self.fileReferenceNumber = convert_double_dwordlong(infile.read(16))
    
    def pFileReferenceNumber(self, infile):
        if self.majorVersion == 2:
            self.pFileReferenceNumber = convert_dwordlong(infile.read(8))
        elif self.majorVersion == 3:
            self.pFileReferenceNumber = convert_double_dwordlong(infile.read(16))

    def usn(self, infile):
        self.usn = convert_dwordlong(infile.read(8))
    
    def timestamp(self, infile):
        self.timestamp = convertTimestamp(convert_dwordlong(infile.read(8)))

    def reason(self, infile):
        self.reason = convertReason(convert_dword(infile.read(4)))
    
    def sourceInfo(self, infile):
        self.sourceInfo = convert_dword(infile.read(4))
    
    def securityId(self, infile):
        self.securityId = convert_dword(infile.read(4))

    def fileAttributes(self, infile):
        self.fileAttributes = convertAttributes(convert_dword(infile.read(4)))

    def fileNameLength(self, infile):
        self.fileNameLength = convert_word(infile.read(2))

    def fileNameOffset(self, infile):
        self.fileNameOffset = convert_word(infile.read(2))

    def filename(self, infile):
        filename = struct.unpack("{}s".format(self.fileNameLength), infile.read(self.fileNameLength))[0]
        self.filename = filename.replace("\x00", "")


def main():
    p = ArgumentParser()
    p.add_argument("journal", help="Parse the specified USN journal")
    p.add_argument("-c", "--csv", help="Return USN records in comma-separated format", action="store_true")
    p.add_argument("-f", "--filename", help="Returns USN record matching a given filename")
    p.add_argument("-i", "--info", help="Returns information about the USN Journal file itself", action="store_true")
    p.add_argument("-l", "--last", help="Return all USN records for the last n days")
    p.add_argument("-q", "--quick", help="Parse a large journal file quickly", action="store_true")
    p.add_argument("-v", "--verbose", help="Return all USN properties", action="store_true")
    args = p.parse_args()

    if os.path.exists(args.journal):
        fileSize = os.path.getsize(args.journal)
    else:
        sys.exit("[ - ] File not found at the specified location")

    with open(args.journal, "rb") as f:
        if args.quick:
            if fileSize > 1073741824:
                dataPointer = findDataQuick(f)
                f.seek(dataPointer)
            else:
                sys.exit("[ - ] The USN journal file must be at least 1GB in size " \
                         "to use the '--quick' functionality\n[ - ] Exitting...")
        else:
            findFirstRecord(f)

        if args.info:
            percentage = str(float(datapointer)/fileSize)
            usn = ParseUsn(f)
        
            print "[ + ] File size (bytes): {}".format(fileSize)
            print "[ + ] Leading null bytes consume ~{}% of the journal file".format(percentage[2:4])
            print "[ + ] Pointer to first USN record: {}".format(datapointer)
            print "[ + ] Timestamp on first USN record: {}".format(usn.timestamp)

        elif args.verbose:
            while True:
                nextrecord = findNextRecord(f, fileSize)
                usn = ParseUsn(f)
                prettyPrint(usn)
                f.seek(nextrecord)

        elif args.filename:
            while True:
                nextrecord = findNextRecord(f, fileSize)
                usn = ParseUsn(f)
                if args.filename.lower() in usn.filename.lower():
                    prettyPrint(usn)
                f.seek(nextrecord)

        elif args.last:
            while True:
                dates = daysago(args.last)
                nextrecord = findNextRecord(f, fileSize)
                usn = ParseUsn(f)
                if usn.timestamp[0:10] in dates:
                    prettyPrint(usn)
                f.seek(nextrecord)

        elif args.csv:
            print "timestamp,filename,fileattr,reason"
            while True:
                nextrecord = findNextRecord(f, fileSize)
                usn = ParseUsn(f)
                print "{},{},{}".format(usn.timestamp, usn.filename, usn.reason)
                f.seek(nextrecord)
                
        else:
            while True:
                nextrecord = findNextRecord(f, fileSize)
                usn = ParseUsn(f)
                print "{} | {} | {}".format(usn.timestamp, usn.filename, usn.reason)
                f.seek(nextrecord)



if __name__ == '__main__':
    main()


