from argparse import ArgumentParser
import collections
from datetime import datetime,timedelta
import json
import os
import struct
import sys


usn_reasons = {
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

file_attributes = {
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



def find_data(usnhandle, filesize):
    # Taken and modified from Dave Lassalle's "parseusn.py"
    # https://github.com/sans-dfir/sift-files/blob/master/scripts/parseusn.py

    if filesize >= 5368709120:
        while True:
            usnhandle.seek(1073741824, 1)
            data = usnhandle.read(6553600)
            data = data.lstrip("\x00")

            if data:
                f.seek((-1073741824 + 6553600), 1)
                while True:
                    data = usnhandle.read(6553600)
                    data = data.lstrip("\x00")
                    if data:
                        return usnhandle.tell() - len(data)
    else:
        while True:
            data = usnhandle.read(6553600)
            data = data.lstrip('\x00')
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
    # Returns the file attributes property in a human-readable format

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


def parse_usn(usnhandle):
    # Returns a dict object containing the USN structure's properties

    recordlen = struct.unpack_from("I", usnhandle.read(4))[0]

    if recordlen:
        nextrecord = (f.tell() - 4) + recordlen
        f.seek(-4, 1)
        usnrecord = collections.OrderedDict()
        usnrecord["recordlen"] = struct.unpack_from("I", usnhandle.read(4))[0]
        usnrecord["majversion"] = struct.unpack_from("h", usnhandle.read(2))[0]
        usnrecord["minversion"] = struct.unpack_from("h", usnhandle.read(2))[0]

        if usnrecord["majversion"] == 2:
            usnrecord["fileref"] = struct.unpack_from("q", usnhandle.read(8))[0]
            usnrecord["pfilerefef"] = struct.unpack_from("q", usnhandle.read(8))[0]

        elif usnrecord["majversion"] == 3:
            usnrecord["filerefer"] = struct.unpack_from("2q", usnhandle.read(16))[0]
            usnrecord["pfileref"] = struct.unpack_from("2q", usnhandle.read(16))[0]
        else:
            sys.exit("[ - ] Unknown USN record version at {}".format(f.tell() - 4))

        usnrecord["usn"] = struct.unpack_from("q", usnhandle.read(8))[0]
        usnrecord["timestamp"] = struct.unpack_from("q", usnhandle.read(8))[0]
        usnrecord["reason"] = struct.unpack_from("I", usnhandle.read(4))[0]
        usnrecord["sourceinfo"] = struct.unpack_from("i", usnhandle.read(4))[0]
        usnrecord["sid"] = struct.unpack_from("I", usnhandle.read(4))[0]
        usnrecord["fileattr"] = struct.unpack_from("I", usnhandle.read(4))[0]
        usnrecord["filenamelen"] = struct.unpack_from("h", usnhandle.read(2))[0]
        usnrecord["filenameoffset"] = struct.unpack_from("h", usnhandle.read(2))[0]
        usnrecord["filename"] = struct.unpack("{}s".format(usnrecord["filenamelen"]), usnhandle.read(usnrecord["filenamelen"]))[0]

        usnrecord["filename"] = usnrecord["filename"].replace("\x00", "")
        usnrecord["fileattr"] = convert_attributes(usnrecord["fileattr"])
        usnrecord["reason"] = convert_reason(usnrecord["reason"])
        usnrecord["timestamp"] = convert_timestamp(usnrecord["timestamp"])

        usnhandle.seek(nextrecord)
        if usnrecord:
            return usnrecord

    else:
        usnhandle.seek(-4, 1)
        try:
            while not struct.unpack_from("I", usnhandle.read(4))[0]:
                continue
        except Exception, e:
            if struct.error:
                if f.tell() == fsize:
                    sys.exit()
        usnhandle.seek(-4, 1)

def daysago(n):
    # Return a list of dates between today and n days ago
    # The dates have been truncated for string searches in
    # the USN records
    
    dates = []
    counter = 0

    while counter < int(n):
        date = str(datetime.now() - timedelta(days=counter))
        dates.append(date[0:10])
        counter += 1
    
    return dates



p = ArgumentParser()
p.add_argument("journal", help="Parse the specified USN journal")
p.add_argument("-c", "--csv", help="Return USN records in comma-separated format", action="store_true")
p.add_argument("-f", "--filename", help="Returns USN record matching a given filename")
p.add_argument("-l", "--last", help="Return all USN records for the last n days")
p.add_argument("-v", "--verbose", help="Return all USN properties", action="store_true")
args = p.parse_args()

if not os.path.exists(args.journal):
    sys.exit("[ - ] File not found at the specified location")

with open(args.journal, "rb") as f:
    fsize = os.path.getsize(args.journal)
    datapointer = find_data(f, fsize)
    f.seek(datapointer)

    if args.verbose:
        while f.tell() < fsize:
            usn = parse_usn(f)
            print json.dumps(parse_usn(f), indent=4)

    elif args.filename:
        while f.tell() < fsize:
            usn = parse_usn(f)
            if args.filename.lower() in usn["filename"].lower():
                print json.dumps(usn, indent=4)

    elif args.last:
        while f.tell() < fsize:
            dates = daysago(args.last)
            usn = parse_usn(f)
            if usn["timestamp"][0:10] in dates:
                print json.dumps(usn, indent=4)

    elif args.csv:
        print "timestamp,filename,fileattr,reason"
        while f.tell() < fsize:
            usn = parse_usn(f)
            print "{},{},{},{}".format(usn["timestamp"], usn["filename"], usn["fileattr"], usn["reason"])
                

    else:
        while f.tell() < fsize:
            usn = parse_usn(f)
            print "{} | {} | {}\n".format(usn["timestamp"], usn["filename"], usn["reason"])














