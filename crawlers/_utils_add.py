#-*- encoding: utf-8 -*-

import os
import sys

PRJNAME = 'ru_corner'
DATA_DIR_NAME = '_data'
CURR_PATH = os.path.abspath(sys.argv[0])


def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

_path = splitall(CURR_PATH)
_sub_idx = None
for idx, dir_ in reversed(list(enumerate(_path))):
    if dir_.lower() == PRJNAME.lower():
        _sub_idx = idx + 1
        break
else:
    raise ValueError('ERROR: invalid path')
