#!python -u
#-*- encoding: utf-8 -*-

from mordl import LemmaTagger
import os
import re


HYPHEN = '-'
HYPHENS_FN = 'hyphens.txt'
HYPHENS_RAW_FN = 'hyphens-raw.txt'
HYPHENS_DONE_FN = 'hyphens-done.txt'
CONJOINTS_FN = 'conjoints.txt'
DISJOINTS_FN = 'disjoints.txt'
ENDINGS_FN = 'endings.txt'
ENDING_RANGE, MIN_ENDING_NUM = 3, 1
NUMBER_TPL, ANY_TPL, ENDING_TPL = '0', '*', '='

re0 = re.compile(rf'(\S+{HYPHEN}\S+)')
re1 = re.compile(r'[^\d.,]')
re2 = re.compile(r'\d')
re3 = re.compile(r'[A-Za-z]')
re4 = re.compile(r'[ЁА-Яёа-я]')

hyphens, hyphens_low = set(), set()
lefts, rights, endings = set(), set(), {}

def get_tpl(fn):
    tpl = []
    if os.path.isfile(fn):
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

with open(HYPHENS_RAW_FN, 'rt', encoding='utf-8') as f:
    for line in f:
        for hyphen in re0.findall(line):
            frags = hyphen.split(HYPHEN)
            if not re1.search(frags[0]):
                for frag in frags[1:]:
                    if re1.search(frag):
                        break
                else:
                    continue  # only digits
                frags[0] = NUMBER_TPL
            else:
                r2 = bool(re2.search(hyphen))
                r3 = bool(re3.search(hyphen))
                r4 = bool(re4.search(hyphen))
                if r2 + r3 + r4 > 1:
                    continue  # rus/lat
                has_middle_caps = False
                for frag in frags:
                   frag1 = frag[1:]
                   if frag1 != frag1.lower():
                       has_middle_caps = True
                if has_middle_caps:
                    continue  # middle caps
            hyphen = f'{frags[0]}{HYPHEN}{frags[-1]}'
            hyphens.add(hyphen)
            if hyphen == hyphen.lower():
                hyphens_low.add(hyphen)
            if len(frags[0]) >= 7:
                lefts.add(frags[0].lower())
            if len(frags[-1]) >= 7:
                rights.add(frags[-1].lower())

def process_frags(frags):
    for frag1 in frags:
        for frag2 in frags:
            if frag1 != frag2 and frag1[:4] == frag2[:4]:
                afxs = LemmaTagger.find_affixes(frag1, frag2)
                stem, afx1, afx2 = afxs[1], afxs[2], afxs[5]
                if len(afx1) <= ENDING_RANGE \
               and len(afx2) <= ENDING_RANGE:
                    if afx1:
                        endings[afx1] = endings.get(afx1, 0) + 1
                    if afx2:
                        endings[afx2] = endings.get(afx2, 0) + 1

process_frags(lefts)
process_frags(rights)

with open(ENDINGS_FN, 'wt', encoding='utf-8') as f:
    for afx, num in sorted(endings.items(), key=lambda x: x[0]):
        if num >= MIN_ENDING_NUM:
            print(afx, file=f)

stems_left, stems_right = set(), set()
for hyphen in sorted(hyphens):
    hyphen_low = hyphen.lower()
    if hyphen_low == hyphen or hyphen_low not in hyphens_low:
        left, right = hyphen.split(HYPHEN)
        for i in range(-ENDING_RANGE, 0):
           if left[i:] in endings:
               left = left[:i]
               if left not in stems_left:
                   stems_left.add(left)
               break
        for i in range(-ENDING_RANGE, 0):
           if right[i:] in endings:
               right = right[:i]
               if right not in stems_right:
                   stems_right.add(right)
               break

tokens = set()
with open(HYPHENS_FN, 'wt', encoding='utf-8') as f, \
     open(HYPHENS_DONE_FN, 'wt', encoding='utf-8') as f_done:
    for hyphen in sorted(hyphens):
        hyphen_low = hyphen.lower()
        if hyphen_low == hyphen or hyphen_low not in hyphens_low:
            left, right = hyphen.split(HYPHEN)
            max_len, do_dis = 0, None
            for re_left, re_right, re_len, do_dis_ in rex:
                if re_len > max_len and re_left.match(left.lower()) \
                                    and re_right.match(right.lower()):
                    max_len = re_len
                    do_dis = do_dis_
            #for i in range(-ENDING_RANGE, 0):
            #   if left[i:] in endings:
            #       left = left[:i] + ENDING_TPL
            #       break
            #if left in stems_left:
            #    left += ENDING_TPL
            #for i in range(-ENDING_RANGE, 0):
            #   if right[i:] in endings:
            #       right = right[:i] + ENDING_TPL
            #       break
            #if right in stems_right:
            #    right += ENDING_TPL
            token = f'{left}{HYPHEN}{right}'
            if token not in tokens:
                tokens.add(token)
                if do_dis is None:
                    print(f'{left}{HYPHEN}{right}', file=f)
                else:
                    sp = ' ' if do_dis else ''
                    print(f'{left}{sp}{HYPHEN}{sp}{right}', file=f_done)
            hyphens_low.add(hyphen_low)
