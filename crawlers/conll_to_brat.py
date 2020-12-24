#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from corpuscula import Conllu
import glob
import os

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
    with open(out_fn, 'wt', encoding='utf-8') as out_f, \
         open(out_fn[:-4] + '.ann', 'w'):
        for sent_no, sent in enumerate(Conllu.load(fn, fix=False,
                                                   log_file=None)):
            if sent_no:
                print(file=out_f)
                if 'newpar id' in sent[1]:
                    print(file=out_f)
            for tok_no, tok in enumerate(sent[0]):
                if tok_no:
                    print('   ', end='', file=out_f)
                print(tok['FORM'], end='', file=out_f)
