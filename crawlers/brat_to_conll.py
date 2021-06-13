#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

import glob
import os
import sys
from toxine import brat

from _utils_add import _path, _sub_idx, DATA_DIR_NAME


assert len(sys.argv) == 3, \
    'ERROR: Syntax is: {} <domain> <source>'.format(sys.argv[0])
domain, source = sys.argv[1:]

def setdir_(*suffixes):
    dir_ = os.path.join(*_path[:_sub_idx], DATA_DIR_NAME, *suffixes)
    if not os.path.isdir(dir_):
        os.makedirs(dir_)
    return dir_

BRAT_DIR = setdir_('..', 'corpus', 'ner', 'brat')
CONLL_DIR = setdir_('brat', 'conll')

for fn in glob.glob(BRAT_DIR + '/{}/{}/*.txt'.format(domain, source),
                    recursive=True):
    print(fn)
    out_fn = fn.replace(BRAT_DIR, CONLL_DIR)
    out_dir = os.path.dirname(out_fn)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    brat.brat_to_conllu(fn, save_to=out_fn, keep_tokens='smart', store_raw_to='raw.txt')
    #brat.brat_to_conllu(fn, save_to=out_fn, keep_tokens=True)
