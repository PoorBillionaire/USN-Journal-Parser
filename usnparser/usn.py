#!/usr/bin/python
#
# Copyright 2017 Adam Witt
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contact: <accidentalassist@gmail.com>


from __future__ import print_function

import os
import sys
import json
import struct
import collections
from argparse import ArgumentParser
from datetime import datetime,timedelta


reasons = collections.OrderedDict()
reasons[0x1] = u'DATA_OVERWRITE'
reasons[0x2] = u'DATA_EXTEND'
reasons[0x4] = u'DATA_TRUNCATION'
reasons[0x10] = u'NAMED_DATA_OVERWRITE'
reasons[0x20] = u'NAMED_DATA_EXTEND'
reasons[0x40] = u'NAMED_DATA_TRUNCATION'
reasons[0x100] = u'FILE_CREATE'
reasons[0x200] = u'FILE_DELETE'
reasons[0x400] = u'EA_CHANGE'
reasons[0x800] = u'SECURITY_CHANGE'
reasons[0x1000] = u'RENAME_OLD_NAME'
reasons[0x2000] = u'RENAME_NEW_NAME'
reasons[0x4000] = u'INDEXABLE_CHANGE'
reasons[0x8000] = u'BASIC_INFO_CHANGE'
reasons[0x10000] = u'HARD_LINK_CHANGE'
reasons[0x20000] = u'COMPRESSION_CHANGE'
reasons[0x40000] = u'ENCRYPTION_CHANGE'
reasons[0x80000] = u'OBJECT_ID_CHANGE'
reasons[0x100000] = u'REPARSE_POINT_CHANGE'
reasons[0x200000] = u'STREAM_CHANGE'
reasons[0x80000000] = u'CLOSE'


attributes = collections.OrderedDict()
attributes[0x1] = u'READONLY'
attributes[0x2] = u'HIDDEN'
attributes[0x4] = u'SYSTEM'
attributes[0x10] = u'DIRECTORY'
attributes[0x20] = u'ARCHIVE'
attributes[0x40] = u'DEVICE'
attributes[0x80] = u'NORMAL'
attributes[0x100] = u'TEMPORARY'
attributes[0x200] = u'SPARSE_FILE'
attributes[0x400] = u'REPARSE_POINT'
attributes[0x800] = u'COMPRESSED'
attributes[0x1000] = u'OFFLINE'
attributes[0x2000] = u'NOT_CONTENT_INDEXED'
attributes[0x4000] = u'ENCRYPTED'
attributes[0x8000] = u'INTEGRITY_STREAM'
attributes[0x10000] = u'VIRTUAL'
attributes[0x20000] = u'NO_SCRUB_DATA'


sourceInfo = collections.OrderedDict()
sourceInfo[0x1] = u'DATA_MANAGEMENT'
sourceInfo[0x2] = u'AUXILIARY_DATA'
sourceInfo[0x4] = u'REPLICATION_MANAGEMENT'


def parseUsn(infile, usn):
    recordProperties = [
        u'majorVersion',
        u'minorVersion',
        u'fileReferenceNumber',
        u'parentFileReferenceNumber',
        u'usn',
        u'timestamp',
        u'reason',
        u'sourceInfo',
        u'securityId',
        u'fileAttributes',
        u'filenameLength',
        u'filenameOffset'
    ]
    recordDict = dict(zip(recordProperties, usn))
    recordDict[u'filename'] = filenameHandler(infile, recordDict)
    recordDict[u'reason'] = convertAttributes(reasons, recordDict[u'reason'])
    recordDict[u'fileAttributes'] = convertAttributes(attributes, recordDict[u'fileAttributes'])
    recordDict[u'humanTimestamp'] = filetimeToHumanReadable(recordDict[u'timestamp'])
    recordDict[u'epochTimestamp'] = filetimeToEpoch(recordDict[u'timestamp'])
    recordDict[u'timestamp'] = filetimeToEpoch(recordDict[u'timestamp'])
    recordDict[u'mftSeqNumber'], recordDict[u'mftEntryNumber'] = convertFileReference(recordDict[u'fileReferenceNumber'])
    recordDict[u'pMftSeqNumber'], recordDict[u'pMftEntryNumber'] = convertFileReference(recordDict[u'parentFileReferenceNumber'])
    return recordDict


def findFirstRecord(infile):
    # Returns a pointer to the first USN record found
    # Modified version of Dave Lassalle's 'parseusn.py'
    # https://github.com/sans-dfir/sift-files/blob/master/scripts/parseusn.py
    while True:
        data = infile.read(65536).lstrip(b'\x00')
        if data:
            return infile.tell() - len(data)


def findNextRecord(infile, journalSize):
    # There are runs of null bytes between USN records. I'm guessing
    # this is done to ensure that journal records are cluster-aligned
    # on disk.
    # This function reads through these null bytes, returning an offset
    # to the first byte of the the next USN record.

    while True:
        try:
            recordLength = struct.unpack_from('<I', infile.read(4))[0]
            if recordLength:
                infile.seek(-4, 1)
                return infile.tell() + recordLength
        except struct.error:
            if infile.tell() >= journalSize:
                sys.exit()


def filetimeToHumanReadable( filetime):
    # Borrowed from Willi Ballenthin's parse_usnjrnl.py
    try:
        return str(datetime.utcfromtimestamp(float(filetime) * 1e-7 - 11644473600))
    except ValueError:
        pass


def filetimeToEpoch(filetime):
    return int(filetime / 10000000 - 11644473600)


def convertFileReference(buf):
    sequenceNumber = (buf >> 48) & 0xFFFF
    entryNumber = buf & 0xFFFFFFFFFFFF
    return sequenceNumber, entryNumber


def filenameHandler(infile, recordDict):
    try:
        filename = struct.unpack_from('<{}s'.format(
            recordDict[u'filenameLength']),
            infile.read(recordDict[u'filenameLength']))[0]
        return filename.decode('utf16')
    except UnicodeDecodeError:
        return u''


def convertAttributes(attributeType, data):
    attributeList = [attributeType[i] for i in attributeType if i & data]
    return u' '.join(attributeList)


def main():
    p = ArgumentParser()
    p.add_argument('-b', '--body', help='Return USN records in comma-separated format', action='store_true')
    p.add_argument('-c', '--csv', help='Return USN records in comma-separated format', action='store_true')
    p.add_argument('-f', '--file', help='Parse the given USN journal file', required=True)
    p.add_argument('-o', '--outfile', help='Parse the given USN journal file', required=True)
    p.add_argument('-s', '--system', help='System name (use with -t)')
    p.add_argument('-t', '--tln', help='TLN ou2tput (use with -s)', action='store_true')
    p.add_argument('-v', '--verbose', help='Return all USN properties for each record (JSON)', action='store_true')
    args = p.parse_args()

    journalSize = os.path.getsize(args.file)
    with open(args.file, 'rb') as i:
        with open(args.outfile, 'wb') as o:
            i.seek(findFirstRecord(i))

            if args.csv:
                o.write(u'timestamp,filename,fileattr,reason\n'.encode('utf-8', errors='backslashreplace'))
                while True:
                    nextRecord = findNextRecord(i, journalSize)
                    recordLength = struct.unpack_from('<I', i.read(4))[0]
                    recordData = struct.unpack_from('<2H4Q4I2H', i.read(56))
                    u = parseUsn(i, recordData)
                    u = u'{0},{1},{2},{3}\n'.format(
                        u[u'humanTimestamp'],
                        u[u'filename'],
                        u[u'fileAttributes'],
                        u[u'reason'])
                    o.write(u.encode('utf8', errors='backslashreplace'))
                    i.seek(nextRecord)

            elif args.body:
                while True:
                    nextRecord = findNextRecord(i, journalSize)
                    recordLength = struct.unpack_from('<I', i.read(4))[0]
                    recordData = struct.unpack_from('<2H4Q4I2H', i.read(56))
                    u = parseUsn(i, recordData)
                    u = u'0|{0} (USN: {1})|{2}-{3}|0|0|0|0|{4}|{4}|{4}|{4}\n'.format(
                        u[u'filename'],
                        u[u'reason'],
                        u[u'mftEntryNumber'],
                        u[u'mftSeqNumber'],
                        u[u'epochTimestamp'],
                        u[u'epochTimestamp'],
                        u[u'epochTimestamp'],
                        u[u'epochTimestamp'])

                    o.write(u.encode('utf8', errors='backslashreplace'))
                    i.seek(nextRecord)

            elif args.tln:
                if not args.system:
                    args.system = u''
                while True:
                    nextRecord = findNextRecord(i, journalSize)
                    recordLength = struct.unpack_from('<I', i.read(4))[0]
                    recordData = struct.unpack_from('<2H4Q4I2H', i.read(56))
                    u = parseUsn(i, recordData)
                    u = u'{0}|USN|{1}||{2}:{3}\n'.format(
                        u[u'epochTimestamp'],
                        args.system,
                        u[u'filename'],
                        u[u'reason'])

                    o.write(u.encode('utf8', errors='backslashreplace'))
                    i.seek(nextRecord)

            elif args.verbose:
                while True:
                    nextRecord = findNextRecord(i, journalSize)
                    recordLength = struct.unpack_from('<I', i.read(4))[0]
                    recordData = struct.unpack_from('<2H4Q4I2H', i.read(56))
                    u = json.dumps(parseUsn(i, recordData), indent=4, ensure_ascii=False)
                    o.write(u.encode('utf8', errors='backslashreplace'))
                    o.write(u'\n')
                    i.seek(nextRecord)

            else:
                while True:
                    nextRecord = findNextRecord(i, journalSize)
                    recordLength = struct.unpack_from('<I', i.read(4))[0]
                    recordData = struct.unpack_from('<2H4Q4I2H', i.read(56))
                    u = parseUsn(i, recordData)
                    u = u'{0} | {1} | {2} | {3}\n'.format(
                        u[u'humanTimestamp'],
                        u[u'filename'],
                        u[u'fileAttributes'],
                        u[u'reason'])

                    o.write(u.encode('utf8', errors='backslashreplace'))
                    i.seek(nextRecord)


if __name__ == '__main__':
    main()


