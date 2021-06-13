#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from copy import deepcopy
from corpuscula import Conllu
import glob
import os
from pathlib import Path

CONLL_DIR = '_0'
EDITED_DIR = '_1'

TOKEN = '$'

for fn in glob.glob(CONLL_DIR + '/*/*.txt', recursive=True):
    print(fn)
    corpus = list(Conllu.load(fn))

    start_spaces = []
    for sentence in corpus:
        sent, meta = sentence
        if 'par_text' in meta:
            parts = meta['par_text'].split(TOKEN)
            start_spaces = [x[:1] == ' ' for x in parts[1:]]

        if not start_spaces:
            continue

        if 'text' not in meta:
            continue

        parts = meta['text'].split(TOKEN)
        if len(parts) > 1:
            text = parts[0]
            for start_space, part in zip(start_spaces, parts[1:]):
                text += TOKEN
                if start_space:
                    text += ' '
                text += part.lstrip()
            meta['text'] = text

        multi_tokens = []
        space_idx = 0
        for tok_idx, tok in enumerate(sent):
            id_, form, misc = tok['ID'], tok['FORM'], tok['MISC']
            if TOKEN in form and ('-' in id_ or form != TOKEN):
                raise ValueError('ERROR: Already edited?')

            if form == TOKEN:
                if tok_idx and not start_spaces[space_idx]:
                    next_tok = sent[tok_idx + 1]
                    tok['MISC']['SpaceAfter'] = 'No'
                    multi_token = Conllu.from_sentence([form + next_tok['FORM']])[0]
                    multi_token['ID'] = '{}-{}'.format(id_, next_tok['ID'])
                    multi_token['MISC'] = deepcopy(next_tok['MISC'])
                    multi_tokens.append((tok_idx, multi_token))
                space_idx += 1

        for idx, tok in reversed(multi_tokens):
            sent.insert(idx, tok)

        start_spaces = start_spaces[len(parts) - 1:]

    path = str(Path(fn).absolute())
    path = path.replace(CONLL_DIR, EDITED_DIR)
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir()
    Conllu.save(corpus, path)
