#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from copy import deepcopy
from corpuscula import Conllu
import glob
import os
from pathlib import Path

DIR = r'C:\prj-git\_mine\ru_corner\_data\conll\newswire'
TOKEN = '%'
log = open('_splitted', 'wt', encoding='utf-8')

parent_fn = None
for fn in glob.glob(DIR + '/*/*.txt', recursive=True):
    corpus = list(Conllu.load(fn, fix=False, log_file=None))
    path = Path(fn)

    for idx, sentence in enumerate(corpus):
        sent, meta = sentence

        prev_id = None
        for idx_, tok in enumerate(sent):
            id_ = tok['ID']
            if id_ == prev_id:
                if parent_fn and parent_fn != fn:
                   print(file=log)
                parent_fn = fn
                print('{} ({}) - {} : {} / {} "{} {}"'
                          .format(meta['sent_id'], idx, id_,
                                  path.parent.name, path.name,
                                  sent[idx_ - 1]['FORM'], tok['FORM']),
                      file=log)
            prev_id = id_

log.close()
