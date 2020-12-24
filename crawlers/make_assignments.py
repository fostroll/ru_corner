#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

import glob
import os
import shutil
import sys

from _utils_add import _path, _sub_idx, DATA_DIR_NAME


opers = sys.argv[1:]
assert opers, 'ERROR: Usage: {} <oper1> <oper2> ...'.format(sys.argv[0])

def setdir_(suffix):
    dir_ = os.path.join(*_path[:_sub_idx], DATA_DIR_NAME, suffix)
    if not os.path.isdir(dir_):
        os.makedirs(dir_)
    return dir_

CONLL_DIR = setdir_('conll')
BRAT_DIR = setdir_('brat')
UNTAGGED_DIR = os.path.join(BRAT_DIR, 'untagged')
ASSIGNMENTS_DIR = os.path.join(BRAT_DIR, 'assignments')
assert os.path.isdir(UNTAGGED_DIR), \
    'ERROR: The directory {} does not exist yet'.format(UNTAGGED_DIR)
assert not os.path.isdir(ASSIGNMENTS_DIR), \
    'ERROR: The directory {} already exists'.format(ASSIGNMENTS_DIR)

max_pass, oper_no, max_oper = len(opers) + 1, 0, len(opers) - 1
for fn in sorted(glob.glob(UNTAGGED_DIR + '/*/*/*.txt', recursive=True)):
    for pass_no in range(1, max_pass):
        out_fn = fn.replace(UNTAGGED_DIR,
                            os.path.join(ASSIGNMENTS_DIR,
                                         'pass{}'.format(pass_no),
                                         opers[oper_no]))
        out_dir = os.path.dirname(out_fn)
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        shutil.copy2(fn, out_dir)
        shutil.copy2(fn[:-4] + '.ann', out_dir)
        oper_no = 0 if oper_no == max_oper else oper_no + 1
    oper_no = 0 if oper_no == max_oper else oper_no + 1
