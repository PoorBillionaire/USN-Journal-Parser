#!/usr/bin/env bash

unzip tests/usnjrnl.zip
usn.py -h
usn.py --quick -f usnjrnl.bin
usn.py -f usnjrnl.bin
usn.py --csv -f usnjrnl.bin
usn.py --verbose -f usnjrnl.bin
usn.py --tln -f usnjrnl.bin
usn.py --tln --system ThisIsASystemName -f usnjrnl.bin
usn.py --body -f usnjrnl.bin
usn.py --body -f usnjrnl.bin > body.txt
mactime -b body.txt

