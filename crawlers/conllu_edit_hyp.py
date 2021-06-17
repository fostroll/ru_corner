#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from copy import deepcopy
from corpuscula import Conllu
import glob
import os
from pathlib import Path

CONLL_DIR = r'C:\prj-git\_mine\ru_corner\_data\conll\newswire'
EDITED_DIR = '_0'

TOKEN = '%'

for fn in glob.glob(CONLL_DIR + '/*/*.txt', recursive=True):
    print(fn)
    corpus = list(Conllu.load(fn))

    end_spaces = []
    for sentence in corpus:
        sent, meta = sentence
        if 'par_text' in meta:
            parts = meta['par_text'].split(TOKEN)
            end_spaces = [x[-1:] == ' ' for x in parts[:-1]]

        if not end_spaces:
            continue

        if 'text' not in meta:
            continue

        parts = meta['text'].split(TOKEN)
        if len(parts) > 1:
            text = ''
            for end_space, part in zip(end_spaces, parts[:-1]):
                text += part.rstrip()
                if end_space:
                    text += ' '
                text += TOKEN
            text += parts[-1]
            meta['text'] = text

        multi_tokens = []
        space_idx = 0
        for tok_idx, tok in enumerate(sent):
            id_, form, misc = tok['ID'], tok['FORM'], tok['MISC']
            if TOKEN in form and ('-' in id_ or form != TOKEN):
                raise ValueError('ERROR: Already edited?')

            if form == TOKEN:
                if tok_idx and not end_spaces[space_idx]:
                    prev_tok = sent[tok_idx - 1]
                    prev_tok['MISC']['SpaceAfter'] = 'No'
                    multi_token = Conllu.from_sentence([prev_tok['FORM'] + form])[0]
                    multi_token['ID'] = '{}-{}'.format(prev_tok['ID'], id_)
                    multi_token['MISC'] = deepcopy(misc)
                    multi_tokens.append((tok_idx - 1, multi_token))
                space_idx += 1

        for idx, tok in reversed(multi_tokens):
            sent.insert(idx, tok)

        end_spaces = end_spaces[len(parts) - 1:]

    path = str(Path(fn).absolute())
    path = path.replace(CONLL_DIR, EDITED_DIR)
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir()
    Conllu.save(corpus, path)
