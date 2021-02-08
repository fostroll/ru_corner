#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

import glob
import os
from toxine import brat

from _utils_add import _path, _sub_idx, DATA_DIR_NAME


def setdir_(suffix):
    dir_ = os.path.join(*_path[:_sub_idx], DATA_DIR_NAME, suffix)
    if not os.path.isdir(dir_):
        os.makedirs(dir_)
    return dir_

CONLL_DIR = setdir_('conll')
BRAT_DIR = setdir_('brat')
UNTAGGED_DIR = os.path.join(BRAT_DIR, 'untagged')

for fn in glob.glob(CONLL_DIR + '/*/*/*.txt', recursive=True):
    out_fn = fn.replace(CONLL_DIR, UNTAGGED_DIR)
    out_dir = os.path.dirname(out_fn)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    brat.conllu_to_brat(fn, out_fn, spaces=3)
