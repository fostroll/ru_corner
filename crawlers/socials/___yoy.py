#!/usr/bin/env python
# coding: utf-8

import glob

for fn in glob.glob('*/*/*.txt'):
    with open(fn, 'rt', encoding='utf-8') as f:
        text = f.read()
        text = text.replace('й', 'й').replace('ё', 'ё')
    with open(fn, 'wt', encoding='utf-8') as f:
        f.write(text)
