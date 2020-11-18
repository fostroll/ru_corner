#-*- encoding: utf-8 -*-

import glob
import os
import sys

PRJNAME = 'ru_corner'
CURRPATH = os.path.abspath(sys.argv[0])
CURRDIR = os.path.dirname(CURRPATH)
TMPDIR = os.path.join(CURRDIR[:CURRDIR.rfind(PRJNAME) + len(PRJNAME)],
                      'data', '_tmp')
DATADIR = CURRPATH[:-3].replace('crawlers', 'data')
CHUNKS_FOR_DOMAIN = 10000
_cnt = len(glob.glob(os.path.join(CURRDIR, '*.py')))
CHUNKS_FOR_SOURCE = CHUNKS_FOR_DOMAIN // _cnt \
                  + (CHUNKS_FOR_DOMAIN % _cnt != 0)
CHUNK_WORDS = 100

def get_tmpdir():
    if not os.path.isdir(TMPDIR):
        os.makedirs(TMPDIR)
    return TMPDIR

def get_datadir():
    if not os.path.isdir(DATADIR):
        os.makedirs(DATADIR)
    return DATADIR
