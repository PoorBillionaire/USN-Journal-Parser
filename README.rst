USN-Journal-Parser
====================      
Python script to parse the NTFS USN Change Journal

Description
-------------
The NTFS USN Change journal is a volume-specific log  which records metadata changes to files. It is a treasure trove of information during a forensic investigation. The change journal is a named alternate data stream, located at: $Extend\\$UsnJrnl:$J. usn.py is a script written in Python which parses the journal's contents, and features several different output formats.

Default Output
----------------
With no command-line options set, usn.py will produce USN journal records in the format below:

::

    dev@computer:$ python usn.py -f usnjournal -o /tmp/usn.txt
    dev@computer:$ cat /tmp/usn.txt

    2016-01-26 18:56:20.046268 | test.vbs | ARCHIVE  | DATA_OVERWRITE DATA_EXTEND 

Command-Line Options
-----------------------

::

    usage: usn.py [-h] [-b] [-c] -f FILE -o OUTFILE [-s SYSTEM] [-t] [-V] [-v]

    usnparser v5.0.0

    optional arguments:
      -h, --help            show this help message and exit
      -b, --body            Return USN records in body file format
      -c, --csv             Return USN records in comma-separated format
      -f FILE, --file FILE  Parse the given USN journal file
      -o OUTFILE, --outfile OUTFILE
                            Output records to given file
      -s SYSTEM, --system SYSTEM
                            System hostname (use with -t)
      -t, --tln             TLN ou2tput (use with -s)
      -V, --verbose         Return all USN properties for each record (JSON)
      -v, --version         show program's version number and exit

**--csv**

Using the CSV flag will, as expected, provide results in CSV format. Using the --csv / -c option provides the same USN fields as default output:

* Timestamp
* Filename
* File attributes
* Reason

An example of what this looks like is below:

::

    dev@computer:~$python usn.py --csv -f usnjournal -o /tmp/usn.txt
    dev@computer:~$ cat /tmp/usn.txt

    timestamp,filename,fileattr,reason
    2015-10-09 21:37:58.836242,A75BFDE52F3DD8E6.dat,ARCHIVE NOT_CONTENT_INDEXED,DATA_EXTEND FILE_CREATE

**--body**

Using the --body / -b command-line flag, the script will output in mactime body format:

::

    dev@computer:~$ python usn.py -f usnjournal --body

    0|schedule log.xml (USN: DATA_EXTEND DATA_TRUNCATION CLOSE)|24603-1|0|0|0|0|1491238176|1491238176|1491238176|1491238176

**--tln / -t**

Using the --tln / -t command-line flag, the script will output in TLN body format:

::

    dev@computer:~$ python usn.py -f usnjournal --tln

    1491238176|USN|||schedule log.xml;DATA_EXTEND DATA_TRUNCATION CLOSE


Add the --system / -s flag to specify a system name with TLN output:

::

    dev@computer:~$ python usn.py -f usnjournal --tln --system ThisIsASystemName

    1491238176|USN|ThisIsASystemName||schedule log.xml;DATA_EXTEND DATA_TRUNCATION CLOSE

**--verbose**

Return all USN members for each record with the --verbose / -v flag. The results are JSON-formatted.

::

    dev@computer:~$python usn.py --verbose -f usnjournal -o /tmp/usn.txt
    dev@computer:~$cat /tmp/usn.txt

    {
        "filename": "62e4f811156dd101d900000084088c08.Specialize.xml",
        "humanTimestamp": "2016-02-22 02:02:23.371990",
        "timestamp": "01d16d1511f8e462",
        "epochTimestamp": 1456106543371,
        "usn": 8389448,
        "fileReferenceNumber": 844424930229305,
        "parentFileReferenceNumber": 281474976725213,
        "reason": "DATA_EXTEND FILE_CREATE",
        "fileAttributes": "ARCHIVE",
        "mftSeqNumber": 3,
        "mftEntryNumber": 97337,
        "pMftSeqNumber": 1,
        "pMftEntryNumber": 14557,
        "filenameLength": 94,
        "filenameOffset": 60,
        "sourceInfo": 0,
        "securityId": 0,
        "majorVersion": 2,
        "minorVersion": 0
    }

Installation
--------------
Using setup.py:

::
    
    python3 setup.py install
    
Using pip:

::
    
    python3 -m pip install usnparser

