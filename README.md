# USN-Journal-Parser
Python script to parse the NTFS USN Journal

###Description
The NTFS USN journal is a volume-specific file which essentially logs changes to files and file metadata. As such, it can be a treasure trove of information during DFIR investigations. The change journal is located at $Extend\$UsnJrnl:$J and can be easily extracted using Encase or FTK.

usn.py is a script written in Python which parses the journal - and has what I consider to be a couple of unique features.

###Command-Line Options

```
positional arguments:
  journal               Parse the specified USN journal

optional arguments:
  -h, --help            show this help message and exit
  -c, --csv             Return USN records in comma-separated format
  -f FILENAME, --filename FILENAME
                        Returns USN record matching a given filename
  -l LAST, --last LAST  Return all USN records for the last n days
  -q, --quick           Parse a large journal file quickly
  -v, --verbose         Return all USN properties
```

####--csv

Using the CSV flag will, as expected, provide results in CSV format. For now, using the --csv / -c option will provide just the timestamp of the change, the name of the file which has been changed, the changed file's file attributes, and the reason for the change that occurred. At this point the --csv flag cannot be combined with any other flag other than --quick which I will detail later. That will be changed soon as I want --csv capability for any data returned.

An example of what this looks like is below

```
dev@computer:~$python usn.py usnJRNL --csv

timestamp,filename,fileattr,reason
2015-10-09 21:37:58.836242,A75BFDE52F3DD8E6.dat,ARCHIVE NOT_CONTENT_INDEXED,DATA_EXTEND FILE_CREATE
```

####--verbose

To obtail all information from a given USN record, use the --verbose / -v flag. This will return each record as a JSON object.

An example of what this looks like:

```
dev@computer:~$python usn.py usnJRNL --verbose

{
    "recordlen": 88, 
    "majversion": 2, 
    "minversion": 0, 
    "fileref": 281474976767661, 
    "pfilerefef": 844424930233360, 
    "usn": 419506120, 
    "timestamp": "2015-10-09 21:38:52.160484", 
    "reason": "CLOSE FILE_DELETE", 
    "sourceinfo": 0, 
    "sid": 0, 
    "fileattr": "ARCHIVE", 
    "filenamelen": 24, 
    "filenameoffset": 60, 
    "filename": "wmiutils.dll"
}
```

####--filename
Sometimes during a more targeted investigation, an Analyst is simply looking for additional supporting evidence to confirm what is believed and does not want to eyeball the entire journal for this evidence. By using the 'filename' command-line flag, an Analyst can return only USN records which contain the given string in its 'filename' attribute:

```
dev@computer:~$ python usn.py usnJRNL --filename jernuhl

{
    "recordlen": 88, 
    "majversion": 2, 
    "minversion": 0, 
    "fileref": 5910974510924810, 
    "pfilerefef": 1688849860348307, 
    "usn": 461014088, 
    "timestamp": "2015-10-28 01:59:56.233596", 
    "reason": "FILE_CREATE", 
    "sourceinfo": 0, 
    "sid": 0, 
    "fileattr": "ARCHIVE", 
    "filenamelen": 22, 
    "filenameoffset": 60, 
    "filename": "jernuhl.txt"
}
```

####---last
In the same vain as the --filename / -f functionality, perhaps the Analyst only wants USN records for a certain range of dates. This is somewhat possible through usn.py - by specifying the last n number of days, the script will return only USN journal records for those days:

```
dev@computer:~$ python usn.py usnJRNL --last 7
{
    "recordlen": 136, 
    "majversion": 2, 
    "minversion": 0, 
    "fileref": 844424930247194, 
    "pfilerefef": 281474976710685, 
    "usn": 452708840, 
    "timestamp": "2015-10-28 00:46:51.412002", 
    "reason": "CLOSE FILE_DELETE", 
    "sourceinfo": 0, 
    "sid": 0, 
    "fileattr": "ARCHIVE", 
    "filenamelen": 72, 
    "filenameoffset": 60, 
    "filename": "$TxfLogContainer00000000000000000003"
}

...
...
...
```

####--quick
One of the main pain points when reviewing a USN journal is its size. These files can easily scale over 20GB. Additionally, often times the USN journal file is comprised of a large amount of leading \x00 values. In many cases 90% of the file is an arbitrary number of null bytes - this means our script needs to first search for and find the actual data before it can begin parsing properly.

Using an interpreted language such as Perl or Python to do this searching can be extremely time consuming if an Analyst is staring at a 40GB journal file. Applying the --quick / -q flag enables the script to perform this search much more quickly, by jumping ahead a gigabyte at a time looking for data. In my experience this functionality works extremely well; however its logic does make some assumptions abou the data and could use more testing.

Below is an example of the time it takes to find valid data in a large USN journal - 39GB in size. This example is not using the --quick functionality and takes over six minutes to even begin parsing data:

```
PS Dev:\Desktop> Measure-Command {C:\Python27\python.exe usn.py usnJRNL}

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
```

Now the same USN journal file, but with the --quick flag invoked. The time it takes to find data is cut down to just under three seconds:

```
PS Dev:\Desktop> Measure-Command {C:\Python27\python.exe usn.py usnJRNL --quick}

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
```
