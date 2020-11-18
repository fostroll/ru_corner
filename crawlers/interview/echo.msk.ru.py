#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
from html import unescape
import json
import os
import random
import re
import requests
from textdistance import damerau_levenshtein
distance = damerau_levenshtein.distance

###
import sys
sys.path.append('../')
###
import utils


SEED = None  #42
ROOT_URL = 'https://echo.msk.ru'
URL = ROOT_URL + '/guests/letter/{i}/page/{j}.html'
START, END = 1040, 1071 + 1
DATA_DIR = utils.get_datadir()
LINKS_FN = os.path.join(DATA_DIR, 'links.txt')
ENDINGS = ['―', ':']

links = []

if os.path.isfile(LINKS_FN):
    with open(LINKS_FN, 'rt') as f:
        for link in f:
            links.append(link.replace('\n', '').replace('\r', ''))

else:
    re0 = re.compile('<div class="author type1 \w+">\s*'
                     '<a class="dark" href="([^">]+)">')
    for i in range(END - START):
        print('{} (of {}):'.format(i, END - START), end='')
        url_ = URL.replace('{i}', str(START + i))
        j = 1
        while True:
            print('' if j == 1 else ',', j, end='')
            url = url_.replace('{j}', str(j))
            res = requests.get(url, allow_redirects=True)
            res = res.text
            res = re0.findall(res)
            if res:
                for link in res:
                    #print('>>>>', link)
                    links.append(ROOT_URL + link)
            else:
                break
            j += 1
        print()

    with open(LINKS_FN, 'wt') as f:
        for link in links:
            print(link, file=f)

def normalize_chunk(lines):
    elen = len(lines)
    speakers = [('', 0)] * elen
    thresh = min(0, max(elen // 10, 1))
    for idx, line in enumerate(lines):
        elen_ = len(line)
        new_key, new_shift = key, _ = speakers[idx]
        if new_shift < 0:
            continue
        for shift, token in enumerate(line[new_shift:], start=new_shift + 1):
            token_ = token.replace('.', '').replace('-', '')
            isend = False
            if not token_.isalpha():
                if True in [x in ENDINGS for x in token_]:
                #if token_[:-1].isalpha() and token_[-1] in ENDINGS:
                    isend = True
                else:
                    continue
            if not isend and shift < elen_ and line[shift].islower():
                break
            if not isend and len(token_) > 1 and shift < elen_ \
                         and token_.isupper() and not line[shift].isupper():
                isend = True
            new_key += token
            if not isend and shift < elen_ and line[shift].isupper():
                continue
            if not isend and shift < elen_ and line[shift].istitle() \
                                           and line[shift][-1] in ENDINGS:
                continue
            value_ = 0
            speakers_ = []
            for idx_, line_ in enumerate(lines):
                key_, shift_ = speakers[idx_]
                if key_ == key:
                    new_key_ = key_
                    for new_shift_, token_ in enumerate(line_[shift_:],
                                                        start=shift_ + 1):
                        new_key_ += token_
                        if len(new_key_) < len(new_key):
                            continue
                        elif new_key_ == new_key:
                            value_ += 1
                            key_ = new_key_
                            shift_ = -shift if isend else new_shift_
                        break
                speakers_.append((key_, shift_))
            if value_ > thresh:
                key = (new_key, shift)
                speakers = speakers_
            else:
                break
            if isend:
                break

    speaker_list = OrderedDict()
    for key, _ in speakers:
        if key:
            speaker_list[key] = speaker_list.setdefault(key, 0) + 1
    speaker_list_ = {}
    for key, value in speaker_list.items():
        #if not len(speaker_list_) and value == 1:
        #    continue
        speaker_list_[key] = value
    speaker_list = {x: y for x, y in speaker_list_.items()
                        if y > thresh
                       and (True in [x_ in ENDINGS for x_ in x]
                       #and (x[-1] in ENDINGS
                        or (len(x) > 1 and x.isupper()))}

    speaker_map = {}
    val = 0
    for key, value in reversed(sorted(speaker_list.items(),
                                      key=lambda x: x[1])):
        for k in speaker_map:
            if distance(key, k) <= 2 and speaker_list[k] / value > 5:
                speaker_map[key] = k
                break
        else:
            speaker_map[key] = key
    #print(speaker_list)
    #print(speaker_map)

    '''
    for i, (key, value) in speakers:
        if key:
            key = speaker_map.get(key, '')
        speakers[i] = key
    '''
    lines_ = []
    for (key, shift), line in zip(speakers, lines):
        if key:
            key = speaker_map.get(key, '')
            if key:
                line = line[abs(shift):]
        lines_.append('{}\t{}'.format(key, ' '.join(line)))
    return lines_

if SEED:
    random.seed(SEED)
random.shuffle(links)
re0 = re.compile('<a href="([^">]+)" class="view">')
re1 = re.compile('<script type="application/ld\+json">(\{.+\})</script>')
re2 = re.compile('<blockquote(?:.|\n)+?</blockquote>')
re3 = re.compile('<.*?>')
total_chunks = 0
for link in links:
    #link = 'https://echo.msk.ru/programs/razbor_poleta/2249838-echo/'
    #link = 'https://echo.msk.ru/programs/kulshok/1901048-echo/'
    #link = 'https://echo.msk.ru/programs/razvorot/576294-echo/'
    res = requests.get(link, allow_redirects=True)
    res = res.text
    pos = res.find('<input class="calendar"')
    if pos > 0:
        res = res[pos:]
    pos = res.find('<div class="moregiant">')
    if pos > 0:
        res = res[:pos]
    res = re0.findall(res)
    if res:
        links_ = []
        for link in res:
            #print('>>>>', link)
            links_.append(ROOT_URL + link)
        if len(links_) > 1:
            random.shuffle(links)
        link = links_[0]
        #with open('111', 'wt', encoding='utf-8') as f:
        #    print(link, file=f)
        res = requests.get(link, allow_redirects=True)
        res = res.text
        #with open('111', 'at', encoding='utf-8') as f:
        #    print(res, file=f)
        pos = res.find('itemprop="articleBody"')
        if pos > 0:
            res = res[pos:]
            pos = res.find('</div>')
            if pos > 0:
                res = res[:pos]
                res = re2.sub('', res)
                res = res.replace('\r', '') \
                         .replace('<br>', '\n').replace('</p>', '\n')
                res = re3.sub('', '<' + res)
                txt = unescape(res)
                #with open('222', 'wt', encoding='utf-8') as f:
                #    print(txt, file=f)
                lines = [x.split()
                             for x in [x.strip() for x in txt.split('\n')
                                           if not x.isupper()]
                             if x]
                if len(lines) <= 10:
                    continue
                total_chunks += 1
                lines = normalize_chunk(lines)
                with open(os.path.join(DATA_DIR, (
                    '{:0' + str(len(str(utils.CHUNKS_FOR_SOURCE))) + 'd}'
                ).format(total_chunks)), 'wt', encoding='utf-8') as f:
                    print(link, file=f, end='\n\n')
                    for line in lines:
                        print(line, file=f)
                print('\r{} (of {})'.format(total_chunks,
                                            utils.CHUNKS_FOR_SOURCE), end='')
                '''
                pos = random.randint(6, len(lines) - 5)
                res = []
                elen = 0
                for i in range(pos, len(lines)):
                    line = lines[i]
                    res.append(line)
                    #elen += len([x for x in line if x.isalpha()])
                    elen += len(line)
                    if i >= 4 and elen >= utils.CHUNK_WORDS:
                        break
                if elen < utils.CHUNK_WORDS:
                    for i in reversed(range(pos)):
                        line = lines[i]
                        res.insert(0, line)
                        #elen += len([x for x in line if x.isalpha()])
                        elen += len(line)
                        if elen >= utils.CHUNK_WORDS:
                            break
                #with open('444', 'wt', encoding='utf-8') as f:
                #    for line in res:
                #        print(' '.join(line), file=f)
                #exit()
                '''
    if total_chunks >= utils.CHUNKS_FOR_SOURCE:
        break
