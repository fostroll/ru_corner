#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from corpuscula import Conllu
import glob
import os
import sys

from _utils_add import _path, _sub_idx, DATA_DIR_NAME


assert len(sys.argv) == 3, \
    'ERROR: Syntax is: {} <domain> <source>'.format(sys.argv[0])
domain, source = sys.argv[1:]

def setdir_(*suffixes):
    dir_ = os.path.join(*_path[:_sub_idx], DATA_DIR_NAME, *suffixes)
    if not os.path.isdir(dir_):
        os.makedirs(dir_)
    return dir_

ORIG_DIR = setdir_('conll')
BRAT_DIR = setdir_('brat', 'conll')
OUT_DIR = setdir_('..', 'corpus', 'ner', 'conll')

for fn in glob.glob(ORIG_DIR + '/{}/{}/*.txt'.format(domain, source),
                    recursive=True):
    print(fn)
    brat_fn = fn.replace(ORIG_DIR, BRAT_DIR)
    out_fn = fn.replace(ORIG_DIR, OUT_DIR)[:-4] + '.conllu'
    out_dir = os.path.dirname(out_fn)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    Conllu.save(Conllu.merge(fn, brat_fn, ignore_new_meta=True), out_fn)
