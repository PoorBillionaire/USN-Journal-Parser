#!/usr/bin/env bash

unzip usnjrnl.zip
../usnparser/usn.py -h
../usnparser/usn.py -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
../usnparser/usn.py --csv -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
../usnparser/usn.py --verbose -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
../usnparser/usn.py --tln -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
../usnparser/usn.py --tln --system ThisIsASystemName -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
../usnparser/usn.py --body -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
#../usnparser/usn.py --body -f usnjrnl.bin -o /tmp/usn.txt
mactime -b /tmp/usn.txt
