#-*- encoding: utf-8 -*-

import glob
import os
import sys

PRJNAME = 'ru_corner'
CURR_PATH = os.path.abspath(sys.argv[0])
CURR_DIR = os.path.dirname(CURR_PATH)

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

_data_dir_name = 'data'
_path = splitall(CURR_PATH)
_sub_idx = None
for idx, dir_ in reversed(list(enumerate(_path))):
    if dir_.lower() == PRJNAME:
        _sub_idx = idx + 1
        break
else:
    raise ValueError('ERROR: invalid path')
TEMP_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, '_tmp')
SOURCE_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, 'source',
                          *_path[_sub_idx + 1:])[:-3]
CHUNKS_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, 'chunks',
                          *_path[_sub_idx + 1:])[:-3]
CHUNKS_FOR_DOMAIN = 10000
_cnt = len(glob.glob(os.path.join(CURR_DIR, '*.py')))
CHUNKS_FOR_SOURCE = CHUNKS_FOR_DOMAIN // _cnt \
                  + (CHUNKS_FOR_DOMAIN % _cnt != 0)
CHUNK_WORDS = 100

def get_temp_dir():
    if not os.path.isdir(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    return TEMP_DIR

def get_source_dir():
    if not os.path.isdir(SOURCE_DIR):
        os.makedirs(SOURCE_DIR)
    return SOURCE_DIR

def get_chunks_dir():
    if not os.path.isdir(CHUNKS_DIR):
        os.makedirs(CHUNKS_DIR)
    return CHUNKS_DIR
