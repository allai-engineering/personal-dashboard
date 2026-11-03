#!/usr/bin/python3 -I
"""Pin the current publisher path before Python loads any release code."""
from pathlib import Path
import os
import sys

CURRENT=Path('/opt/cpa-dashboard/current')


def main():
    if len(sys.argv)!=1:raise SystemExit(64)
    target=(CURRENT/'cockpit_publish.py').resolve(strict=True)
    os.execv('/usr/bin/python3',['/usr/bin/python3','-I','-B',str(target)])


if __name__=='__main__':main()
