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
LINKS_FN = os.path.join(utils.TEXTS_DIR, 'links')
ENDINGS = ['-', '–', '—', '―', ':']

if SEED:
    random.seed(SEED)

links = []

if os.path.isfile(LINKS_FN):
    with open(LINKS_FN, 'rt') as f:
        links = [x for x in f.read().split('\n') if x]

else:
    re0 = re.compile('<div class="author type1 \w+">\s*'
                     '<a class="dark" href="([^">]+)">')
    for i in range(END - START):
        print('{} (of {}):'.format(i + 1, END - START), end='')
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
                    links.append(ROOT_URL + link)
            else:
                break
            j += 1
        print()

    random.shuffle(links)
    with open(LINKS_FN, 'wt') as f:
        f.write('\n'.join(links))

text_fns = utils.get_file_list(utils.TEXTS_DIR, len(links))
total_texts = len(text_fns)
if total_texts < utils.TEXTS_FOR_SOURCE:
    start_link_idx = int(os.path.split(sorted(text_fns)[-1])[-1]
                             .replace(utils.DATA_EXT, '')) \
                         if total_texts > 0 else \
                     0

    def extend_key(key, token):
        if key and key[-1].isalpha() and token[0].isalpha():
            key += ' '
        return key + token

    def normalize_text(lines):
        elen = len(lines)
        speakers = [('', 0)] * elen
        thresh = min(0, max(elen // 10, 1))
        for idx, line in enumerate(lines):
            elen_ = len(line)
            new_key, new_shift = key, _ = speakers[idx]
            if new_shift < 0:
                continue
            for shift, token in enumerate(line[new_shift:],
                                          start=new_shift + 1):
                token_ = token.replace('.', '')
                isend = False
                if not token_.isalpha():
                    if True in [x in ENDINGS for x in token_]:
                        isend = True
                    else:
                        continue
                new_key = extend_key(new_key, token)
                if not isend and shift < elen_:
                    next_token = line[shift]
                    if next_token.islower():
                        break
                    if len(token_) > 1 and token_.isupper() \
                                       and not next_token.isupper() \
                                       and not next_token in ENDINGS:
                        isend = True
                    if next_token.isupper():
                        continue
                    if next_token.istitle() and next_token[-1] in ENDINGS:
                        continue
                value_ = 0
                speakers_ = []
                for idx_, line_ in enumerate(lines):
                    key_, shift_ = speakers[idx_]
                    if key_ == key:
                        new_key_ = key_
                        for new_shift_, token_ in enumerate(line_[shift_:],
                                                            start=shift_ + 1):
                            new_key_ = extend_key(new_key_, token_)
                            if len(new_key_) < len(new_key):
                                continue
                            elif new_key_ == new_key:
                                value_ += 1
                                key_ = new_key_
                                shift_ = -shift - new_shift_ if isend else \
                                         new_shift_
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
            if not len(speaker_list_) and value == 1:
                continue
            speaker_list_[key] = value
        speaker_list = {x: y for x, y in speaker_list_.items()
                            if y > thresh
                           and (True in [x_ in ENDINGS for x_ in x]
                            or (len(x) > 1 and x.isupper())
                            or (len(x) == 1 and x in ENDINGS))}

        speaker_map = {}
        val = 0
        for key, value in reversed(sorted(speaker_list.items(),
                                          key=lambda x: x[1])):
            key_ = key
            for k in speaker_map:
                if distance(key, k) <= 2 and speaker_list[k] / value > 5:
                    key_ = k
                    break
            speaker_map[key] = key_[:-1] \
                                   if len(key_) > 1 \
                                  and key_[-1] in ENDINGS else \
                               key_
        #print(speaker_list)
        #print(speaker_map)

        lines_ = []
        key_lines = 0
        for (key, shift), line in zip(speakers, lines):
            if key:
                key = speaker_map.get(key, '')
                if key:
                    key_lines += 1
                    line = line[abs(shift):]
            line = ' '.join(line)
            if line and line[0] in ENDINGS:
                line = line[1:].lstrip()
            if line:
                lines_.append('{}\t{}'.format(key, line))
        return lines_ if key_lines > utils.MIN_TEXT_LINES else None

    re0 = re.compile('<a href="([^">]+)" class="view">')
    re1 = re.compile('<script type="application/ld\+json">(\{.+\})</script>')
    re2 = re.compile('<blockquote(?:.|\n)+?</blockquote>')
    re3 = re.compile('<b>(.+?)</b>')
    re3a = re.compile('\W')
    re4 = re.compile('<.*?>|\(.*?\)')
    for link_no, link in enumerate(links[start_link_idx:],
                                   start=start_link_idx + 1):
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
                links_.append(ROOT_URL + link)
            if len(links_) > 1:
                random.shuffle(links_)
            link = links_[0]
            #link = 'https://echo.msk.ru/programs/razbor_poleta/2249838-echo/'
            #link = 'https://echo.msk.ru/programs/On_Two_Chairs/1458504-echo/'
            #link = 'https://echo.msk.ru/programs/korzun/1266886-echo/'
            #link = 'https://echo.msk.ru/programs/beseda/15584/'
            res = requests.get(link, allow_redirects=True)
            res = res.text
            pos = res.find('itemprop="articleBody"')
            if pos > 0:
                res = res[pos:]
                pos = res.find('</div>')
                if pos > 0:
                    res = res[:pos]
                    res = re2.sub('', res)
                    res = re3.sub(lambda x: re3a.sub(' ', x.group(1).upper()) + ':', res)
                    res = res.replace('\r', '') \
                             .replace('<br>', '\n').replace('</p>', '\n')
                    res = re4.sub(' ', '<' + res)
                    txt = unescape(res)
                    lines = [
                        x.split()
                            for x in [x.strip() for x in txt.split('\n')]
                            if x and not x.isupper()
                                 and not (len(x) >= 2
                                      and ((x[0] == '(' and x[-1] == ')')
                                        or (x[0] == '[' and x[-1] == ']')
                                        or (x[0] == '«' and x[-1] == '»')))
                    ]
                    lines = normalize_text(lines)
                    if lines:
                        total_texts += 1
                        with open(utils.get_data_path(utils.TEXTS_DIR,
                                                      len(links), link_no),
                                  'wt', encoding='utf-8') as f:
                            print(link, file=f)
                            f.write('\n'.join(lines))
                        print('\r{} (of {})'.format(total_texts,
                                                    utils.TEXTS_FOR_SOURCE),
                              end='')
                    #exit()
        if total_texts >= utils.TEXTS_FOR_SOURCE:
            break

text_fns = utils.get_file_list(utils.TEXTS_DIR, len(links))
for text_idx, text_fn in enumerate(text_fns[:utils.CHUNKS_FOR_SOURCE],
                                   start=1):
    chunk_fn = text_fn.replace(utils.TEXTS_DIR, utils.CHUNKS_DIR)
    assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
    if not os.path.isfile(chunk_fn):
        with open(text_fn, 'rt', encoding='utf-8') as text_f, \
             open(chunk_fn, 'wt', encoding='utf-8') as chunk_f:
            text = [x.split('\t') for x in text_f.read().split('\n') if x][1:]
            moder = None
            for start_idx, (speaker, _) in enumerate(text):
                if speaker:
                    moder = speaker
                    break
            assert moder, 'ERROR: invalid file content'
            end_idx, next_id = 0, 0
            for idx, (speaker, _) in reversed(list(enumerate(text))):
                if speaker:
                    if not end_idx:
                        end_idx = idx + 1
                    if speaker == moder:
                        end_idx = idx
                        break
                    if next_id > 2:
                        break
                    next_id += 1
            text = text[start_idx:end_idx]
            lines = []
            speaker_no, chunk_words = 0, 0
            for speaker, line in reversed(text):
                lines.insert(0, '\t'.join([speaker, line]))
                chunk_words += len(line.split())
                if speaker:
                    speaker_no += 1
                if speaker_no >= utils.MIN_CHUNK_LINES \
               and chunk_words >= utils.MIN_CHUNK_WORDS:
                    break
            chunk_f.write('\n'.join(lines))
            print('\r{} (of {})'.format(text_idx, utils.CHUNKS_FOR_SOURCE),
                  end='')
