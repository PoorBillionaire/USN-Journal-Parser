#!/usr/bin/python


# Copyright 2015 Adam Witt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contact: <accidentalassist@gmail.com>

from __future__ import print_function

import os
import sys
import json
import time
import struct
import collections
from argparse import ArgumentParser
from datetime import datetime,timedelta


def findFirstRecord(infile):
    # Returns a pointer to the first USN record found
    # Modified version of Dave Lassalle's "parseusn.py"
    # https://github.com/sans-dfir/sift-files/blob/master/scripts/parseusn.py
    while True:
        data = infile.read(65536).lstrip(b"\x00")
        if data:
            return infile.tell() - len(data)

def findFirstRecordQuick(infile, filesize):
    # Same as findFirstRecord(), but initially seeks through larger swaths of
    # NULL bytes to speed the time it takes to parse a larger journal file

    while True:
        if infile.tell() + 1073741824 < filesize:
            infile.seek(1073741824, 1)
            data = infile.read(6553600)
            data = data.lstrip(b"\x00")

            if data:
                infile.seek((-1073741824 + 6553600), 1)
                return findFirstRecord(infile)
        else:
            return findFirstRecord(infile)

def findNextRecord(infile, journalSize):
    # There are runs of null bytes between USN records. I'm guessing
    # this is done to ensure that journal records are cluster-aligned
    # on disk.
    # This function reads through these null bytes, returning an offset
    # to the first byte of the the next USN record.

    while True:
        try:
            recordlen = struct.unpack_from("<I", infile.read(4))[0]
            if recordlen:
                infile.seek(-4, 1)
                return (infile.tell() + recordlen)
        except struct.error:
            if infile.tell() >= journalSize:
                sys.exit()


class Usn(object):
    def __init__(self, infile):
        self.reasons = collections.OrderedDict()
        self.reasons[0x1] = "DATA_OVERWRITE"
        self.reasons[0x2] = "DATA_EXTEND"
        self.reasons[0x4] = "DATA_TRUNCATION"
        self.reasons[0x10] = "NAMED_DATA_OVERWRITE"
        self.reasons[0x20] = "NAMED_DATA_EXTEND"
        self.reasons[0x40] = "NAMED_DATA_TRUNCATION"
        self.reasons[0x100] = "FILE_CREATE"
        self.reasons[0x200] = "FILE_DELETE"
        self.reasons[0x400] = "EA_CHANGE"
        self.reasons[0x800] = "SECURITY_CHANGE"
        self.reasons[0x1000] = "RENAME_OLD_NAME"
        self.reasons[0x2000] = "RENAME_NEW_NAME"
        self.reasons[0x4000] = "INDEXABLE_CHANGE"
        self.reasons[0x8000] = "BASIC_INFO_CHANGE"
        self.reasons[0x10000] = "HARD_LINK_CHANGE"
        self.reasons[0x20000] = "COMPRESSION_CHANGE"
        self.reasons[0x40000] = "ENCRYPTION_CHANGE"
        self.reasons[0x80000] = "OBJECT_ID_CHANGE"
        self.reasons[0x100000] = "REPARSE_POINT_CHANGE"
        self.reasons[0x200000] = "STREAM_CHANGE"
        self.reasons[0x80000000] = "CLOSE"

        self.attributes = collections.OrderedDict()
        self.attributes[0x1] = "READONLY"
        self.attributes[0x2] = "HIDDEN"
        self.attributes[0x4] = "SYSTEM"
        self.attributes[0x10] = "DIRECTORY"
        self.attributes[0x20] = "ARCHIVE"
        self.attributes[0x40] = "DEVICE"
        self.attributes[0x80] = "NORMAL"
        self.attributes[0x100] = "TEMPORARY"
        self.attributes[0x200] = "SPARSE_FILE"
        self.attributes[0x400] = "REPARSE_POINT"
        self.attributes[0x800] = "COMPRESSED"
        self.attributes[0x1000] = "OFFLINE"
        self.attributes[0x2000] = "NOT_CONTENT_INDEXED"
        self.attributes[0x4000] = "ENCRYPTED"
        self.attributes[0x8000] = "INTEGRITY_STREAM"
        self.attributes[0x10000] = "VIRTUAL"
        self.attributes[0x20000] = "NO_SCRUB_DATA"

        self.sourceInfo = collections.OrderedDict()
        self.sourceInfo[0x1] = "DATA_MANAGEMENT"
        self.sourceInfo[0x2] = "AUXILIARY_DATA"
        self.sourceInfo[0x4] = "REPLICATION_MANAGEMENT"

        self.usn(infile)

    def usn(self, infile):
        self.recordLength = struct.unpack_from("<I", infile.read(4))[0]
        self.majorVersion = struct.unpack_from("<H", infile.read(2))[0]
        self.minorVersion = struct.unpack_from("<H", infile.read(2))[0]

        if self.majorVersion == 2:
            self.mftEntryNumber = self.convertFileReference(infile.read(6))
            self.mftSeqNumber = struct.unpack_from("<H", infile.read(2))[0]
            self.parentMftEntryNumber = self.convertFileReference(infile.read(6))
            self.parentMftSeqNumber = struct.unpack_from("<H", infile.read(2))[0]

        elif self.majorVersion == 3:
            self.referenceNumber = struct.unpack_from("<2Q", infile.read(16))[0]
            self.pReferenceNumber = struct.unpack_from("<2Q", infile.read(16))[0]

        self.usn = struct.unpack_from("<Q", infile.read(8))[0]
        self.filetime = struct.unpack_from("<Q", infile.read(8))[0]
        self.humanTimestamp = self.filetimeToHumanReadable(self.filetime)
        self.epochTimestamp = self.filetimeToEpoch(self.filetime)
        reason = struct.unpack_from("<I", infile.read(4))[0]
        self.reason = self.convertAttributes(self.reasons, reason)
        self.sourceInfo = struct.unpack_from("<I", infile.read(4))[0]
        self.securityId = struct.unpack_from("<I", infile.read(4))[0]
        fileAttributes = struct.unpack_from("<I", infile.read(4))[0]
        self.fileAttributes = self.convertAttributes(self.attributes, fileAttributes)
        self.fileNameLength = struct.unpack_from("<H", infile.read(2))[0]
        self.fileNameOffset = struct.unpack_from("<H", infile.read(2))[0]
        filename = struct.unpack("{0}s".format(self.fileNameLength), infile.read(self.fileNameLength))[0]
        self.filename = filename.replace(b"\x00", b"").decode('ascii')


    def prettyPrint(self):
        record = collections.OrderedDict()
        record["recordlen"] = self.recordLength
        record["majversion"] = self.majorVersion
        record["minversion"] = self.minorVersion
        record["mftSequenceNumber"] = self.mftSeqNumber
        record["mftEntryNumber"] = self.mftEntryNumber
        record["parentMftSequenceNumber"] = self.parentMftSeqNumber
        record["parentMftEntryNumber"] = self.parentMftEntryNumber
        record["usn"] = self.usn
        record["timestamp"] = self.humanTimestamp
        record["reason"] = self.reason
        record["sourceinfo"] = self.sourceInfo
        record["sid"] = self.securityId
        record["fileattr"] = self.fileAttributes
        record["filenamelen"] = self.fileNameLength
        record["filenameoffset"] = self.fileNameOffset
        record["filename"] = self.filename

        print(json.dumps(record, indent=4))

    def filetimeToHumanReadable(self, filetime):
        # The USN record's "timestamp" property is a Win32 FILETIME value
        # This function returns that value in a human-readable format
        return str(datetime(1601,1,1) + timedelta(microseconds=filetime / 10.))

    def filetimeToEpoch(sefl, filetime):
        return int(filetime / 10000000 - 11644473600)


    def convertAttributes(self, attributeType, data):
        # Returns the USN reasons attribute in a human-readable format
        attributeList = []

        for i in attributeType:
            if i & data:
                attributeList.append(attributeType[i])
        return " ".join(attributeList)

    def convertFileReference(self, buf):
        b = bytearray(buf)
        byteString = ""

        for i in b[::-1]:
            byteString += format(i, 'x')
        return int(byteString, 16)


def main():
    p = ArgumentParser()
    p.add_argument("-b", "--body", help="Return USN records in comma-separated format", action="store_true")
    p.add_argument("-c", "--csv", help="Return USN records in comma-separated format", action="store_true")
    p.add_argument("-f", "--file", help="Parse the given USN journal file")
    p.add_argument("-q", "--quick", help="Parse a large journal file quickly", action="store_true")
    p.add_argument("-s", "--system", help="System name (use with -t)")
    p.add_argument("-t", "--tln", help="TLN output (use with -s)", action="store_true")
    p.add_argument("-v", "--verbose", help="Return all USN properties for each record (JSON)", action="store_true")
    args = p.parse_args()

    with open(args.file, "rb") as f:
        journalSize = os.path.getsize(args.file)
        dataPointer = findFirstRecord(f)
        f.seek(dataPointer)

        if args.quick:
            if journalSize > 1073741824:
                dataPointer = findFirstRecordQuick(f, journalSize)
                f.seek(dataPointer)
            else:
                sys.exit("[ - ] The USN journal file must be at least 1GB in size " \
                         "to use the '--quick' functionality\n[ - ] Exitting...")
        
        elif args.csv:
            print("timestamp,filename,fileattr,reason")

        elif args.tln:
            if not args.system:
                systemname = ""

        while True:
            nextRecord = findNextRecord(f, journalSize)
            u = Usn(f)
            f.seek(nextRecord)
        
            if args.verbose:
                u.prettyPrint()

            elif args.body:
                print("0|{0} (USN: {1})|{2}-{3}|0|0|0|0|{4}|{4}|{4}|{4}".format(u.filename, u.reason, u.mftEntryNumber, u.mftSeqNumber, u.epochTimestamp))

            elif args.tln:
                print("{0}|USN|{1}||{2}:{3}".format(u.epochTimestamp, systemname, u.filename, u.reason))

            elif args.csv:
                print("{0},{1},{2},{3}".format(u.humanTimestamp, u.filename, u.fileAttributes, u.reason))
                    
            else:
                print("{0} | {1} | {2} | {3}".format(u.humanTimestamp, u.filename, u.fileAttributes, u.reason))

if __name__ == '__main__':
    main()