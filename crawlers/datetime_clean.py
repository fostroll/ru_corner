#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

import glob


for fn in glob.glob('*.ann'):
    with open(fn, 'rt', encoding='utf-8') as f:
        ann = f.read()
    ann = ann.replace('\tDate-absolute', '\tDate') \
             .replace('\tDate-relative', '\tDate') \
             .replace('\tDate-period', '\tDate') \
             .replace('\tDate-duration', '\tDate') \
             .replace('\tTime-absolute', '\tTime') \
             .replace('\tTime-relative', '\tTime') \
             .replace('\tTime-period', '\tTime') \
             .replace('\tTime-duration', '\tTime')
    with open(fn, 'wt', encoding='utf-8') as f:
        f.write(ann)
