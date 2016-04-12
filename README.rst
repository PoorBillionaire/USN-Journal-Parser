USN-Journal-Parser
====================
Python script to parse the NTFS USN Change Journal

Description
-------------
The NTFS USN Change journal is a volume-specific file which logs changes to files and file metadata. As such, it can be a treasure trove of information during an investigation. The change journal is located at $Extend\\$UsnJrnl:$J.

usn.py is a script written in Python which parses the journal's contents - and has what I consider to be a couple of unique features.

Default Output
----------------
With no command-line options set, usn.py will produce USN journal records in the format below:

::

    dev@computer:$ python usn.py -f usnjournal
    2016-01-26 18:56:20.046268 | test.vbs | ARCHIVE  | DATA_OVERWRITE DATA_EXTEND 

Command-Line Options
-----------------------

::

    optional arguments:
      -h, --help            show this help message and exit
      -c, --csv             Return USN records in comma-separated format
      -f FILE, --file FILE  Parse the given USN journal file
      -g GREP, --grep GREP  'grep' for a specific file name in a USN record, and
                            only provide records which match
      -q, --quick           Parse a large journal file quickly
      -v, --verbose         Return all USN properties for each record (JSON)

**--quick**

**Warning: This logic does make (very good) assumptions about the data in question. On the off chance you are experience issues using this functionality just switch back to using usn.py without the --quick flag. Personally, I have never had issues with it.**

The USN Journal is a Sparse File - A major pain point when parsing a USN journal is its size after being extracted to disk. Sparse Files of this nature can easily scale to be dozens of gigabytes in size, comprised of a large swaths of null values. As such, this script needs to 'hunt' for and find the first valid USN record before it can begin producing results.

Using an interpreted language such as Perl or Python to do this initial hunting can be extremely time consuming if an Analyst is working with a large journal file. Applying the --quick / -q flag enables the script to perform this search much more quickly: by jumping ahead a gigabyte at a time looking for data. Jumping ahead one gigabyte at a time requires the journal in question to be at least one gigabyte in size. If it isn't, the script will simply produce an error and exit:

::

    dev@computer$ python usn.py -f usnjournal --quick
    [ - ] This USN journal is not large enough for the --quick functionality
    [ - ] Exitting...

Below is an example of the time it takes to find valid data in a large USN journal - 39GB in size. This example is not using the --quick functionality and takes over six minutes to even begin parsing data:

::

    PS Dev:\Desktop> Measure-Command {C:\Python27\python.exe usn.py -f usnjournal}
    Hours             : 0
    Minutes           : 6
    Seconds           : 3
    Milliseconds      : 766
    Ticks             : 3637662181
    TotalDays         : 0.00421025715393519
    TotalHours        : 0.101046171694444
    TotalMinutes      : 6.06277030166667
    TotalSeconds      : 363.7662181
    TotalMilliseconds : 363766.2181

Now the same USN journal file, but with the --quick flag invoked. The time it takes to find data is cut down to just under three seconds:

::

    PS Dev:\Desktop> Measure-Command {C:\Python27\python.exe usn.py -f usnjournal --quick}
    Hours             : 0
    Minutes           : 0
    Seconds           : 2
    Milliseconds      : 822
    Ticks             : 28224455
    TotalDays         : 3.2667193287037E-05
    TotalHours        : 0.000784012638888889
    TotalMinutes      : 0.0470407583333333
    TotalSeconds      : 2.8224455
    TotalMilliseconds : 2822.4455

**--csv**

Using the CSV flag will, as expected, provide results in CSV format. Using the --csv / -c option provides the same USN fields as default output:

* Timestamp
* Filename
* File attributes
* Reason

At this point the --csv flag cannot be combined with any other flag other than --quick. That should change soon, as I want --csv capability for any data returned. An example of what this looks like is below:

::

    dev@computer:~$python usn.py -f usnjournal --csv
    timestamp,filename,fileattr,reason
    2015-10-09 21:37:58.836242,A75BFDE52F3DD8E6.dat,ARCHIVE NOT_CONTENT_INDEXED,DATA_EXTEND FILE_CREATE

**--verbose**

Return all USN record properties for each entry, with the --verbose / -v flag. The results are JSON-formatted.

::

    dev@computer:~$python usn.py -f usnjournal --verbose
    {
        "recordlen": 96, 
        "majversion": 2, 
        "minversion": 0, 
        "mftSequenceNumber": 1, 
        "mftEntryNumber": 95075, 
        "parentMftSequenceNumber": 1, 
        "parentMftEntryNumber": 2221, 
        "usn": 432, 
        "timestamp": "2016-02-22 02:59:26.374840", 
        "reason": "FILE_DELETE CLOSE ", 
        "sourceinfo": 0, 
        "sid": 0, 
        "fileattr": "ARCHIVE ", 
        "filenamelen": 34, 
        "filenameoffset": 60, 
        "filename": "WindowsUpdate.log"
    }

**--grep / -g**

Sometimes during a more targeted search, an Analyst is simply looking for additional supporting evidence to confirm what is believed or pile on to what is already known - and does not want to eyeball the entire journal for this evidence. By using the '--grep / -g' command-line flag, an Analyst can return only USN records which match a given 'filename' attribute:

::

    dev@computer:~$ python usn.py -f usnjournal --grep test.txt

    2016-04-11 00:26:09.324654 | test.txt | ARCHIVE  | FILE_CREATE 
    2016-04-11 00:26:09.324654 | test.txt | ARCHIVE  | FILE_CREATE CLOSE 
    2016-04-11 00:26:09.324654 | test.txt | ARCHIVE  | FILE_DELETE CLOSE 

Installation
--------------
Using setup.py:

::
    
    python setup.py install
    
Using pip:

::
    
    pip install usnparser
