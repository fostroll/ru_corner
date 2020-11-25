#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
from html import unescape
import os
import random
import re

###
import sys
sys.path.append('../')
###
import utils
import _utils


SEED = 42
ROOT_URL = 'https://www.interfax.ru'
URL_1 = '/interview/'
URL_2 = 'page_{}'
URL = ROOT_URL + URL_1
SENT_STARTS = ['-', '–', '—', '―']
SPEAKER_A, SPEAKER_B = 'Вопрос', 'Ответ'
MIN_TEXT_LINES = 4
MIN_CHUNK_LINES = 4

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Downloading of the list of links
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]

else:
    links = OrderedDict()
    re0 = re.compile(r'<div class="allPNav">.+?'
                     r'<a class="active">(\d+)</a></div>')
    re1 = re.compile(r'<a href="({}\d+)" title='.format(URL_1))
    res = utils.get_url(URL)
    page = res.text
    res = re0.search(page)
    assert res, 'ERROR: no page links found on the main page'
    page_no = int(res.group(1))
    while True:
        res = re1.findall(page)
        assert res, \
               'ERROR: no article links found on the page {}'.format(page_no)
        for link in res:
            links[ROOT_URL + link] = 1
        print('\r{}'.format(len(links)), end='')
        if page_no == 1:
            break
        page_no -= 1
        res = utils.get_url(URL + URL_2.format(page_no))
        page = res.text
    links = list(links)

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
    print()

links_num = len(links)

'''===========================================================================
Downloading and parse texts
==========================================================================='''
pages_fns = utils.get_file_list(utils.PAGES_DIR, links_num)
start_link_idx = int(os.path.split(sorted(pages_fns)[-1])[-1]
                         .replace(utils.DATA_EXT, '')) \
                     if len(pages_fns) > 0 else \
                 0
texts_total = 0

re0 = re.compile(r'<article itemprop="articleBody">((?:.|\n)+?)</article>')
re1 = re.compile(r'<p>((?:.|\n)*?)</p>')
re2 = re.compile(r'<.*?>|\(.*?\)')
need_enter = False
for link_no, link in enumerate(links, start=1):
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    #link = 'https://www.interfax.ru/interview/374150'
    page_fn = utils.get_data_path(utils.PAGES_DIR, links_num, link_no)
    text_fn = utils.get_data_path(utils.TEXTS_DIR, links_num, link_no)
    page = None
    if link_no > start_link_idx:
        res = utils.get_url(link, encoding='windows-1251')
        page = res.text
    else:
        if not os.path.isfile(page_fn):
            continue
        if os.path.isfile(text_fn):
            texts_total += 1
            continue
        with open(page_fn, 'rt', encoding='utf-8') as f:
            link = f.readline().rstrip()
            page = f.read()
    res = re0.sub(r'\g<1>', page)
    res = re1.findall(res)
    lines, key_lines = [], 0
    prev_speaker = None
    for line in res:
        line = unescape(line).strip()
        if line.startswith('<b>') or line.startswith('<strong>'):
            speaker = SPEAKER_A
        elif not prev_speaker:
            continue
        else:
            speaker = SPEAKER_B
        line = re2.sub(' ', line).strip()
        if line:
            if line[0] in SENT_STARTS:
               line = line[1:].lstrip()
            if speaker != prev_speaker:
                prev_speaker = speaker
                key_lines += 1
            else:
                speaker = ''
            line = speaker + '\t' + ' '.join(line.split())
            lines.append(line)
    if key_lines >= MIN_TEXT_LINES:
        texts_total += 1
        if link_no > start_link_idx:
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
        with open(text_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            f.write('\n'.join(lines))
        print('\r{} (of {})'.format(texts_total,
                                    min(utils.TEXTS_FOR_SOURCE, links_num)),
              end='')
        need_enter = True
    #exit()
if need_enter:
    print()

'''===========================================================================
Chunks creation
==========================================================================='''
_utils.make_chunks(links_num, trim_ending=False, moderator=SPEAKER_A,
                   min_chunk_lines=MIN_CHUNK_LINES)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(links_num)
