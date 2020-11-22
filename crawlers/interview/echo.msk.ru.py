#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
from html import unescape
import json
import os
import random
import re
from textdistance import damerau_levenshtein
distance = damerau_levenshtein.distance

###
import sys
sys.path.append('../')
###
import utils


SEED = 42
ROOT_URL = 'https://echo.msk.ru'
URL = ROOT_URL + '/guests/letter/{i}/page/{j}.html'
START, END = 1040, 1071 + 1
ENDINGS = ['-', '–', '—', '―', ':']

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Downloading of the list of links
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt') as f:
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
            res = utils.get_url(url)
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
    with open(utils.LINKS_FN, 'wt') as f:
        f.write('\n'.join(links))

links_num = len(links)

'''===========================================================================
Downloading and parse texts
==========================================================================='''
pages_fns = utils.get_file_list(utils.PAGES_DIR, links_num)
texts_total = len(pages_fns)
if texts_total < utils.TEXTS_FOR_SOURCE:
    start_link_idx = int(os.path.split(sorted(pages_fns)[-1])[-1]
                             .replace(utils.DATA_EXT, '')) \
                         if texts_total > 0 else \
                     0
    texts_total = 0

    def extend_key(key, token):
        if key and key[-1].isalpha() and token[0].isalpha():
            key += ' '
        return key + token

    def normalize_text(lines):
        elen = len(lines)
        speakers = [('', 0)] * elen
        thresh = max(elen // 10, 1)
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
                    if any(x in ENDINGS for x in token_):
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
                                shift_ = -new_shift_ if isend else \
                                         new_shift_
                            break
                    speakers_.append((key_, shift_))
                if value_ <= thresh and len(key) > 5 and key.isupper() \
                                    and not new_key.isupper():
                    break
                else:
                    key = new_key
                    speakers = speakers_
                if isend:
                    break

        speaker_list = OrderedDict()
        for key, _ in speakers:
            if key:
                speaker_list[key] = speaker_list.get(key, 0) + 1
        speaker_list_ = {}
        for key, value in speaker_list.items():
            if not len(speaker_list_) and value == 1:
                continue
            speaker_list_[key] = value
        speaker_list = {x: y for x, y in speaker_list_.items()
                            if any(x_ in ENDINGS for x_ in x)
                            or (len(x) > 1 and x.isupper())
                            or (len(x) == 1 and x in ENDINGS)}

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

        lines_, key_lines = [], 0
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
        return lines_ if key_lines >= utils.MIN_TEXT_LINES else None

    re0 = re.compile('<a href="([^">]+)" class="view">')
    re1 = re.compile('<img [^>]+>')
    re2 = re.compile('<blockquote(?:.|\n)+?</blockquote>')
    re3 = re.compile('<b>(.+?)</b>')
    re3a = re.compile('\W')
    re4 = re.compile('<.*?>|\(.*?\)')
    #for link_no, link in enumerate(links[start_link_idx:],
    #                               start=start_link_idx + 1):
    for link_no, link in enumerate(links, start=1):
        page_fn = utils.get_data_path(utils.PAGES_DIR, links_num, link_no)
        text_fn = utils.get_data_path(utils.TEXTS_DIR, links_num, link_no)
        page = None
        if link_no >= start_link_idx:
            res = utils.get_url(link)
            res = res.text
        else:
            if not os.path.isfile(page_fn):
                continue
            if os.path.isfile(text_fn):
                texts_total += 1
                continue
            with open(page_fn, 'rt', encoding='utf-8') as f:
                link = f.readline().rstrip()
                page = res = f.read()
        if not page:
            pos = res.find('<input class="calendar"')
            if pos < 0:
                continue
            res = res[pos:]
            pos = res.find('<div class="moregiant">')
            if pos < 0:
                continue
            res = res[:pos]
            res = re0.findall(res)
        if res:
            if page:
                links_ = [link]
            else:
                links_ = []
                for link in res:
                    links_.append(ROOT_URL + link)
                if len(links_) > 1:
                    slice_ = (links_num + link_no) % len(links_)
                    links_ = links_[slice_:] + links_[:slice_]
            for link in links_:
                #link = 'https://echo.msk.ru/programs/razbor_poleta/2249838-echo/'
                #link = 'https://echo.msk.ru/blog/ssobyanin/2744914-echo/'
                if not page:
                    res = utils.get_url(link)
                    page = res.text
                res = page
                pos = res.find('itemprop="articleBody"')
                if pos > 0:
                    res = res[pos:]
                    pos = res.find('</div>')
                    if pos > 0:
                        res = res[:pos]
                        res = res.replace('\n', ' ')
                        res = re1.sub('{img}', res)
                        res = re2.sub('', res)
                        res = re3.sub(
                            lambda x: re3a.sub(' ', x.group(1).upper()) + ':',
                            res
                        )
                        res = res.replace('\r', '') \
                                 .replace('<br>', '\n').replace('</p>', '\n')
                        res = re4.sub(' ', '<' + res)
                        txt = unescape(res)
                        '''
                        lines = [
                            x.split()
                                for x in [x.strip() for x in txt.split('\n')]
                                if x and (not x.isupper() or '.' in x)
                                     and not (len(x) >= 2
                                          and ((x[0] == '(' and x[-1] == ')')
                                            or (x[0] == '[' and x[-1] == ']')
                                            or (x[0] == '«' and x[-1] == '»')))
                        ]
                        '''
                        lines = []
                        maybe_caption = False
                        for line in [x.strip() for x in txt.split('\n')]:
                            if '{img}' in line:
                                maybe_caption = True
                                continue
                            if line and (not line.isupper() or '.' in line) \
                           and not (len(line) >= 2
                                and ((line[0] == '(' and line[-1] == ')')
                                  or (line[0] == '[' and line[-1] == ']')
                                  or (line[0] == '«' and line[-1] == '»'))) \
                           and (not maybe_caption or not line[-1].isalnum()):
                                lines.append(line.split())
                            maybe_caption = False
                        lines = normalize_text(lines)
                        if lines:
                            texts_total += 1
                            if link_no >= start_link_idx:
                                with open(page_fn,
                                          'wt', encoding='utf-8') as f:
                                    print(link, file=f)
                                    f.write(page)
                            with open(text_fn, 'wt', encoding='utf-8') as f:
                                print(link, file=f)
                                f.write('\n'.join(lines))
                            print('\r{} (of {})'
                                      .format(texts_total,
                                              utils.TEXTS_FOR_SOURCE),
                                  end='')
                            break
                #exit()
        if texts_total >= utils.TEXTS_FOR_SOURCE:
            break
    print()


'''===========================================================================
Chunks creation
==========================================================================='''
utils.make_chunks(links_num)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(links_num)
