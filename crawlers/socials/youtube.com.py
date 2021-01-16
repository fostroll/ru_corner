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
import _youtube
import _utils

SEED = 42
INIT_URL = 'https://whatstat.ru/channels/top500'
ROOT_URL = 'https://www.youtube.com/'
CHANNELS_QUEUE_FN = os.path.join(utils.PAGES_DIR, 'channels_queue')
CHANNELS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'channels_ignore')
AUTHORS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'authors_ignore')
MAX_FILES = 10000

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Links download
==========================================================================='''
need_enter = False
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]

else:
    res = utils.get_url(INIT_URL).text
    pos = res.find('<tbody>')
    if pos > 0:
        res = res[pos + 7:]
    pos = res.find('</tbody>')
    if pos > 0:
        res = res[:pos]
    print(res)
    for link, title in re.findall(r'<a href="/(channel/[^">]+)">.*?([^>]+)</a>', res):
        links.append(ROOT_URL + link + '\t' + title)
    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
if need_enter:
    print()

num_links = len(links)

'''===========================================================================
Texts download and parse
==========================================================================='''
page_fns = utils.get_file_list(utils.PAGES_DIR, MAX_FILES)
texts_total = 0

def parse_page(page):
    text = re.sub(r'<br>', '\n', page)
    text = re.sub(r'<[^>]*>', '', text)
    text0 = []
    for line in text.split('\n'):
        line = unescape(line).replace('\u00a0', ' ') \
                             .replace('\u200b', '') \
                             .replace('\ufeff', '') \
                             .replace('й', 'й').replace('ё', 'ё') \
                             .strip()
        if line:
            text0.append(re.sub(r'\s+', ' ', line))
    return '\n'.join(text0)

need_enter = False
for page_fn in page_fns:
    text_fn = page_fn.replace(utils.PAGES_DIR, utils.TEXTS_DIR)
    if os.path.isfile(text_fn):
        texts_total += 1
        continue
    with open(page_fn, 'rt', encoding='utf-8') as f:
        link = f.readline()
        page = f.read()
    text = parse_page(page)
    if text:
        with open(text_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            f.write(text)
        texts_total += 1
        print('\r{} (of {})'.format(texts_total, utils.TEXTS_FOR_SOURCE),
              end='')
        need_enter = True

if texts_total < utils.TEXTS_FOR_SOURCE:
    if os.path.isfile(CHANNELS_QUEUE_FN):
        with open(CHANNELS_QUEUE_FN, 'rt', encoding='utf-8') as f:
            channels_queue = OrderedDict(x.split('\t')
                                             for x in f.read().split('\n')
                                             if x)
    else:
        channels_queue = OrderedDict(x.split('\t') for x in links)
    if os.path.isfile(CHANNELS_IGNORE_FN):
        with open(CHANNELS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            channels_ignore = OrderedDict(x.split('\t')
                                              for x in f.read().split('\n')
                                              if x)
    else:
        channels_ignore = OrderedDict()
    if os.path.isfile(AUTHORS_IGNORE_FN):
        with open(AUTHORS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            authors_ignore = OrderedDict(x.split('\t')
                                             for x in f.read().split('\n')
                                             if x)
    else:
        authors_ignore = OrderedDict()
    driver = _utils.selenium_init(silent=False)
    for text, page, link in _youtube.crawl(
        channels_queue, min_words=_utils.MIN_CHUNK_WORDS,
        max_words=_utils.MAX_CHUNK_WORDS, post_limit=_utils.POST_LIMIT,
        channels_ignore=channels_ignore, authors_ignore=authors_ignore,
        driver=driver, silent=True
    ):
        if page:
            text = parse_page(page)
            texts_total += 1
            page_fn = utils.get_data_path(utils.PAGES_DIR, MAX_FILES,
                                          texts_total)
            text_fn = utils.get_data_path(utils.TEXTS_DIR, MAX_FILES,
                                          texts_total)
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
            with open(text_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(text)
        with open(CHANNELS_QUEUE_FN, 'wt', encoding='utf-8') as f:
            f.write('\n'.join('\t'.join(x) for x in channels_queue.items()))
        with open(CHANNELS_IGNORE_FN, 'wt', encoding='utf-8') as f:
            f.write('\n'.join('\t'.join(x) for x in channels_ignore.items()))
        with open(AUTHORS_IGNORE_FN, 'wt', encoding='utf-8') as f:
            f.write('\n'.join('\t'.join(x) for x in authors_ignore.items()))
        print('\r{} (of {})'.format(texts_total, utils.TEXTS_FOR_SOURCE),
              end='')
        need_enter = True
        if texts_total >= utils.TEXTS_FOR_SOURCE:
            break
    driver.quit()
if need_enter:
    print()

'''===========================================================================
Chunks creation
==========================================================================='''
_utils.make_chunks(MAX_FILES)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(MAX_FILES, isdialog=False)
