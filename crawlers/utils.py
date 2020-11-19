#-*- encoding: utf-8 -*-

import glob
import os
import sys

PRJNAME = 'ru_corner'
CURR_PATH = os.path.abspath(sys.argv[0])
CURR_DIR = os.path.dirname(CURR_PATH)
DATA_EXT = '.txt'
MIN_TEXT_LINES = 12
MIN_CHUNK_LINES = 6
MIN_CHUNK_WORDS = 200

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
_data_dir_name = 'data'
#TEMP_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, '_tmp')
TEXTS_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, 'texts',
                          *_path[_sub_idx + 1:])[:-3]
CHUNKS_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, 'chunks',
                          *_path[_sub_idx + 1:])[:-3]
CONLL_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, 'conll',
                         *_path[_sub_idx + 1:])[:-3]
TEXTS_FOR_DOMAIN = 10000
_cnt = len(glob.glob(os.path.join(CURR_DIR, '*.py')))
TEXTS_FOR_SOURCE = TEXTS_FOR_DOMAIN // _cnt \
                 + (TEXTS_FOR_DOMAIN % _cnt != 0)
CHUNKS_FOR_DOMAIN = TEXTS_FOR_DOMAIN
CHUNKS_FOR_SOURCE = CHUNKS_FOR_DOMAIN // _cnt \
                  + (CHUNKS_FOR_DOMAIN % _cnt != 0)
CONLL_FOR_DOMAIN = 1000
CONLL_FOR_SOURCE = CONLL_FOR_DOMAIN // _cnt \
                 + (CONLL_FOR_DOMAIN % _cnt != 0)

#if not os.path.isdir(TEMP_DIR):
#    os.makedirs(TEMP_DIR)
if not os.path.isdir(TEXTS_DIR):
    os.makedirs(TEXTS_DIR)
if not os.path.isdir(CHUNKS_DIR):
    os.makedirs(CHUNKS_DIR)
if not os.path.isdir(CONLL_DIR):
    os.makedirs(CONLL_DIR)

def get_data_path(data_dir, max_files, curr_num):
    return os.path.join(data_dir,
                        ('{:0' + str(len(str(max_files))) + 'd}')
                            .format(curr_num)
                      + DATA_EXT)

def get_file_list(data_dir, max_files):
    return glob.glob(
        os.path.join(data_dir,
                     '?' * len(str(max_files)) + DATA_EXT)
    )

def fn_to_id(fn):
    return os.path.split(fn)[-1].replace(DATA_EXT, '')
