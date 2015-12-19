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
import math
import os
import struct
import sys


usn_reasons = collections.OrderedDict(
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

file_attributes = collections.OrderedDict(
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


def find_data(usnhandle):
    # USN journals often start with large amounts of leading zeros before
    # providing any data - this function returns a pointer to where the
    # first USN journal record exists in the file
    #
    # Inspired by Dave Lassalle's "parseusn.py" - but mostly modified
    # https://github.com/sans-dfir/sift-files/blob/master/scripts/parseusn.py

    while True:
        data = usnhandle.read(6553600)
        data = data.lstrip('\x00')
        if data:
            return usnhandle.tell() - len(data)


def find_data_quick(usnhandle, journalsize):
    # In larger USN journals (20GB+), the journal file might lead with gigabytes
    # and gigabytes of leading zeroes. This function essentially does the same as
    # "find_data()"; however it iterates the file in 1GB chunks to start.
    #
    # WARNING: This function makes the assumption that once the USN records appear
    # in the file, the zero bytes between records will never exceed 6553600 bytes.
    # Though in my experience, this shouldn't be an issue. I have never seen or heard
    # of that much space between two records

    if journalsize < 1073741824:
        sys.exit("[ - ] This USN journal is not large enough for the " \
                 "--quick functionality\n[ - ] Exitting...")

    while True:
        if usnhandle.tell() + 1073741824 < journalsize:
            usnhandle.seek(1073741824, 1)
            data = usnhandle.read(6553600)
            data = data.lstrip("\x00")

            if data:
                usnhandle.seek((-1073741824 + 6553600), 1)

                while True:
                    data = usnhandle.read(6553600)
                    data = data.lstrip("\x00")
                    if data:
                        return usnhandle.tell() - len(data)
        else:
            while True:
                data = usnhandle.read(6553600)
                data = data.lstrip("\x00")
                if data:
                    return usnhandle.tell() - len(data)


def convert_timestamp(timestamp):
    # The USN record's "timestamp" property is a Win32 FILETIME value
    # This function returns that value in a human-readable format

    return str(datetime(1601,1,1) + timedelta(microseconds=timestamp / 10.))


def convert_reason(reason):
    # Returns the USN "reason" property in a human-readable format

    reasonlist = []
    formatted = ''

    for item in usn_reasons:
        if item & reason:
            reasonlist.append(usn_reasons[item])

    for item in reasonlist:
        if item != reasonlist[-1]:
            formatted += item + " "
        else:
            formatted += item

    return formatted


def convert_attributes(fileattribute):
    # Returns the USN 'file attributes' property in a human-readable format

    attrlist = []
    formatted = ''
    for item in file_attributes:
        if fileattribute & item:
            attrlist.append(file_attributes[item])
    
    for item in attrlist:
        if item != attrlist[-1]:
            formatted += item + " "
        else:
            formatted += item

    return formatted


def validate_record(usnhandle, journalsize):
    # This function determines the recordlength of a USN record by
    # interpreting its first four bytes. This value is returned.
    #
    # Using the recordlength, it then calculates the start of the next
    # valid USN record. This value is also returned
    #
    # The reason this functionality is broken out, is because the 
    # parse_usn function below was getting bloated and ugly/unreadable

    while True:
        try:
            recordlen = struct.unpack_from("I", usnhandle.read(4))[0]
            usnhandle.seek(-4, 1)
        except Exception, e:
            if (struct.error) and (usnhandle.tell() == journalsize):
                    sys.exit()

        if recordlen:
            nextrecord = (usnhandle.tell() + recordlen)
            return [recordlen, nextrecord]
        else:
             try:
                 while not struct.unpack_from("I", usnhandle.read(4))[0]:
                    continue
             except Exception, e:
                 if (struct.error) and (usnhandle.tell() == journalsize):
                     sys.exit()

        usnhandle.seek(-4, 1)
        continue


def parse_usn(usnhandle, recordlen, nextrecord):
    # Returns a dict object containing the USN structure's properties
    #
    # This function is an eyesore - I would like to split a couple
    # pieces of its functionality out at some point

    usnrecord = collections.OrderedDict()
    usnrecord["recordlen"] = convert_dword(usnhandle.read(4))
    usnrecord["majversion"] = convert_word(usnhandle.read(2))
    usnrecord["minversion"] = convert_word(usnhandle.read(2))

    if usnrecord["majversion"] == 2:
        usnrecord["fileref"] = convert_dwordlong(usnhandle.read(8))
        usnrecord["pfilerefef"] = convert_dwordlong(usnhandle.read(8))

    elif usnrecord["majversion"] == 3:
        usnrecord["filerefer"] = convert_double_dwordlong(usnhandle.read(16))
        usnrecord["pfileref"] = convert_double_dwordlong(usnhandle.read(16))
    else:
        sys.exit("[ - ] Unknown USN record version at {}".format(f.tell() - 4))

    usnrecord["usn"] = convert_dwordlong(usnhandle.read(8))
    usnrecord["timestamp"] = convert_dwordlong(usnhandle.read(8))
    usnrecord["reason"] = convert_dword(usnhandle.read(4))
    usnrecord["sourceinfo"] = convert_dword(usnhandle.read(4))
    usnrecord["sid"] = convert_dword(usnhandle.read(4))
    usnrecord["fileattr"] = convert_dword(usnhandle.read(4))
    usnrecord["filenamelen"] = convert_word(usnhandle.read(2))
    usnrecord["filenameoffset"] = convert_word(usnhandle.read(2))
    usnrecord["filename"] = struct.unpack("{}s".format(usnrecord["filenamelen"]),
                                    usnhandle.read(usnrecord["filenamelen"]))[0]

    usnrecord["filename"] = usnrecord["filename"].replace("\x00", "")
    usnrecord["fileattr"] = convert_attributes(usnrecord["fileattr"])
    usnrecord["reason"] = convert_reason(usnrecord["reason"])
    usnrecord["timestamp"] = convert_timestamp(usnrecord["timestamp"])

    usnhandle.seek(nextrecord)
    if usnrecord:
        return usnrecord


def daysago(n):
    # Return a list of dates between today and n days ago
    # The dates have been truncated for string searches in
    # the USN records when the "--last" CLI option is invoked
    
    dates = []
    counter = 0

    while counter < int(n):
        date = str(datetime.now() - timedelta(days=counter))
        dates.append(date[0:10])
        counter += 1
    
    return dates


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

    if not os.path.exists(args.journal):
        sys.exit("[ - ] File not found at the specified location")

    with open(args.journal, "rb") as f:
        fsize = os.path.getsize(args.journal)

        if args.quick:
            datapointer = find_data_quick(f, fsize)
            f.seek(datapointer)
        else:
            datapointer = find_data(f)
            f.seek(datapointer)

        if args.info:
            recordlength, nextrecord = validate_record(f, fsize)
            percentage = str(float(datapointer)/fsize)
            f.seek(datapointer)
            firstrecord = parse_usn(f, recordlength, nextrecord)
        
            print "[ + ] File size (bytes): {}".format(fsize)
            print "[ + ] Leading null bytes consume ~{}% of the journal file".format(percentage[2:4])
            print "[ + ] Pointer to first USN record: {}".format(datapointer)
            print "[ + ] Timestamp on first USN record: {}".format(firstrecord["timestamp"])

        elif args.verbose:
            while True:
                recordlength, nextrecord = validate_record(f, fsize)
                usn = parse_usn(f, recordlength, nextrecord)
                print json.dumps(usn, indent=4)

        elif args.filename:
            while True:
                recordlength, nextrecord = validate_record(f, fsize)
                usn = parse_usn(f, recordlength, nextrecord)
                if args.filename.lower() in usn["filename"].lower():
                    print json.dumps(usn, indent=4)

        elif args.last:
            while True:
                dates = daysago(args.last)
                recordlength, nextrecord = validate_record(f, fsize)
                usn = parse_usn(f, recordlength, nextrecord)
                if usn["timestamp"][0:10] in dates:
                    print json.dumps(usn, indent=4)

        elif args.csv:
            print "timestamp,filename,fileattr,reason"
            while True:
                recordlength, nextrecord = validate_record(f, fsize)
                usn = parse_usn(f, recordlength, nextrecord)
                print "{},{},{},{}".format(usn["timestamp"], usn["filename"], usn["fileattr"], usn["reason"])
                
        else:
            while True:
                recordlength, nextrecord = validate_record(f, fsize)
                usn = parse_usn(f, recordlength, nextrecord )
                print "{} | {} | {}\n".format(usn["timestamp"], usn["filename"], usn["reason"])

if __name__ == '__main__':
    main()
