#!/usr/bin/env bash

unzip tests/usnjrnl.zip
usn.py -h
usn.py -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
usn.py --csv -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
usn.py --verbose -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
usn.py --tln -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
usn.py --tln --system ThisIsASystemName -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
usn.py --body -f usnjrnl.bin -o /tmp/usn.txt
cat /tmp/usn.txt
usn.py --body -f usnjrnl.bin -o /tmp/usn.txt
mactime -b /tmp/usn.txt
