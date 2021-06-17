#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from copy import deepcopy
from corpuscula import Conllu
import glob
import os
from pathlib import Path
import re

CONLL_DIR = r'C:\prj-git\_mine\ru_corner\_data\conll\newswire'
EDITED_DIR = '_0'
TPL_DIR = r'C:\prj-git\_mine\ru_corner\_data\brat\final\newswire'

HYPHEN = '-'
CONJOINTS_FN = os.path.join(TPL_DIR, 'conjoints.txt')
DISJOINTS_FN = os.path.join(TPL_DIR, 'disjoints.txt')
ENDINGS_FN = os.path.join(TPL_DIR, 'endings.txt')
ENDING_RANGE, MIN_ENDING_NUM = 3, 1
NUMBER_TPL, ANY_TPL, ENDING_TPL = '0', '*', '='

re0 = re.compile(rf'(\S+{HYPHEN}\S+)')
re1 = re.compile(r'[^\d.,]')
re2 = re.compile(r'\d')
re3 = re.compile(r'[A-Za-z]')
re4 = re.compile(r'[ЁА-Яёа-я]')

def get_tpl(fn):
    tpl = []
    with open(fn, 'rt', encoding='utf-8') as f:
        tpl_ = [x.lower() for x in [x.strip()
                          for x in f.read().split('\n')] if x]
    for x in tpl_:
        xs = x.split(HYPHEN)
        if x == HYPHEN or len(xs) > 2:
            raise ValueError(f'ERROR: Invalid template in {fn}: {x}')
        elif len(xs) == 1:
            tpl.append((f'{x}-*', x))
            tpl.append((f'*-{x}', x))
        elif not xs[0]:
            tpl.append((f'*{x}', x))
        elif not xs[1]:
            tpl.append((f'{x}*', x))
        else:
            tpl.append((x, x))
    return tpl

conjoints = get_tpl(CONJOINTS_FN)
disjoints = get_tpl(DISJOINTS_FN)

with open(ENDINGS_FN, 'rt', encoding='utf-8') as f:
    endings = {x.lower().strip(): MIN_ENDING_NUM
                   for x in f.read().split('\n')[:-1]}

re_end_ = '|'.join(endings)

def get_re(tpl):
    return [(('^'
            + x.replace(NUMBER_TPL, r'\d+').replace(ANY_TPL, f'.*')
               .replace(f'{ENDING_TPL}{HYPHEN}', f'(?:{re_end_})?{HYPHEN}')
               .replace(ENDING_TPL, f'(?:{re_end_})?')
               .replace(HYPHEN, rf'${HYPHEN}^')
            + '$').split(HYPHEN), y) for x, y in tpl]

re_cons_ = get_re(conjoints)
re_diss_ = get_re(disjoints)
#print(re_cons_)
#print(re_diss_)
rex = [(re.compile(x[0][0]), re.compile(x[0][1]), len(x[1]), False)
           for x in re_cons_] \
    + [(re.compile(x[0][0]), re.compile(x[0][1]), len(x[1]), True)
           for x in re_diss_]

hyphen_tok = Conllu.from_sentence(['-'])[0]
hyphen_tok['MISC']['SpaceAfter'] = 'Yes'

for fn in glob.glob(CONLL_DIR + '/*/*.txt', recursive=True):
    print(fn)
    corpus = list(Conllu.load(fn))

    end_spaces = []
    for sentence in corpus:
        sent, meta = sentence

        sub_tokens = []
        multi_end_id = None
        for tok_idx, tok in enumerate(sent):
            id_, form, misc = tok['ID'], tok['FORM'], tok['MISC']
            if '-' in id_:
                if multi_end_id:
                    raise ValueError('ERROR: Cross multi-labels')
                multi_end_id = id_.split('-')[-1]
                continue
            if re0.search(form):
                do_dis = None
                hyphen = form
                frags = hyphen.split(HYPHEN)
                if not re1.search(frags[0]):
                    for frag in frags[1:]:
                        if re1.search(frag):
                            frags[0] = NUMBER_TPL
                            break
                    else:
                        do_dis=False  # only digits -> don't split
                else:
                    r2 = bool(re2.search(hyphen))
                    r3 = bool(re3.search(hyphen))
                    r4 = bool(re4.search(hyphen))
                    if r2 + r3 + r4 > 1:
                        do_dis = True  # rus/lat -> always split
                        print('stage 1', form)
                    else:
                        has_middle_caps = False
                        for frag in frags:
                           frag1 = frag[1:]
                           if frag1 != frag1.lower():
                               has_middle_caps = True
                        if has_middle_caps:
                            do_dis = True  # middle caps -> always split
                            print('stage 2', form)

                if do_dis is None:
                    left, right = frags[0], frags[-1]
                    max_len = 0
                    print(left, right)
                    for re_left, re_right, re_len, do_dis_ in rex:
                        if re_len > max_len \
                       and re_left.match(left.lower()) \
                       and re_right.match(right.lower()):
                            max_len = re_len
                            do_dis = do_dis_
                            print(re_len, do_dis_, re_left, re_right)
                    if do_dis:
                        print('stage 3', form)

                if do_dis:
                    if '-' in id_:
                        raise ValueError('ERROR: Already edited?')

                    sub_tok = None
                    for frag in form.split(HYPHEN):
                        if sub_tok:
                            hyphen_tok['ID'] = id_
                            sub_tokens.append((tok_idx + 1,
                                               deepcopy(hyphen_tok)))
                        sub_tok = Conllu.from_sentence([frag])[0]
                        sub_tok['ID'] = id_
                        sub_tok['MISC']['SpaceAfter'] = 'Yes'
                        sub_tokens.append((tok_idx + 1, sub_tok))
                    sub_id = id_ + '0'
                    sub_tok['ID'] = sub_id
                    sub_tok['MISC'] = deepcopy(misc)
                    tok['ID'] = f'{id_}-{sub_id}'

            if id_ == multi_end_id:
                multi_end_id = None

        for idx, tok in reversed(sub_tokens):
            sent.insert(idx, tok)
        #if sub_tokens:
        #    for tok in sent:
        #        print(tok['ID'], tok['FORM'])

    path = str(Path(fn).absolute())
    path = path.replace(CONLL_DIR, EDITED_DIR)
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir()
    Conllu.save(corpus, path)
