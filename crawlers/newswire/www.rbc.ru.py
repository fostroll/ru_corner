#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import time
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
ROOT_URL = 'https://www.rbc.ru'
URL = ROOT_URL + '/short_news'
URL_1 = ROOT_URL + '/v10/ajax/get-news-feed-short/project/rbcnews/lastDate/{}/limit/99'

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
    re0 = re.compile(r'<div class="js-news-feed-item[^"]*" '
                     r'data-modif="(\d+)"')
    re1 = re.compile(r'<a href="([^"]+)" class="item__link">')
    re2 = re.compile(r'<span class="item__title[^"]*">(?:\s|\n)*'
                     r'(?:<span class="item__author">(?:\s|\n)*'
                     r'(?:<!--(?:.|\n)*-->)?([^<]+)(?:<!--(?:.|\n)*-->)?'
                     r'(?:\s|\n)*</span>)?(?:\s|\n)*([^<]+)</span>')
    now = int(time.time()) + 1
    while len(links) <= utils.TEXTS_FOR_SOURCE * 2:
        url = URL_1.format(now)
        print()
        print(url)
        res = utils.get_url(url)
        res = res.json()
        items = res.get('items')
        assert items, 'ERROR: no items on the link ' + url
        for item_no, item in enumerate(items):
            res = item.get('html')
            assert res, \
                'ERROR: invalid format of the record #{} of page {}' \
                    .format(item_no, url)
            res0 = re0.search(res)
            res1 = re1.search(res)
            res2 = re2.search(res)
            assert res0 and res1 and res2, \
                'ERROR: invalid format of data of the record #{} of page {}' \
                    .format(item_no, url)
            now = res0.group(1)
            link = res1.group(1)
            author = res2.group(1)
            title = res2.group(2).strip()
            links[link] = unescape((author.strip() + ': ' if author else '')
                                 + title).strip()
        print('\r{}'.format(len(links)), end='')
        if len(links) > utils.TEXTS_FOR_SOURCE * 2:
            break
    links = list('\t'.join(x) for x in links.items())

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

re2 = re.compile(r'<div itemprop="articleBody" class="article-text-body">'
                 r'((?:.|\n)+?)</div>')
re0 = re.compile(r'<p>((?:.|\n)*?)</p>')
re1 = re.compile(r'<.*?>')
need_enter = False
for link_no, link in enumerate(links, start=1):
    link, header = link.split('\t')
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    #link = 'https://www.interfax.ru/interview/374150'
    page_fn = utils.get_data_path(utils.PAGES_DIR, links_num, link_no)
    text_fn = utils.get_data_path(utils.TEXTS_DIR, links_num, link_no)
    page = None
    if link_no > start_link_idx:
        res = utils.get_url(link)
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
    res = re2.search(page)
    assert res, 'ERROR: no news text on page with link #{} ({})' \
                    .format(link_no, link)
    res = re0.findall(res.group(1))
    lines = []
    for line in res:
        line = unescape(re1.sub('', line)).strip()
        if line.startswith('НОВОСТИ ПО ТЕМЕ:'):
            break
        if line:
            lines.append(' '.join(line.split()))
    if len(lines) >= _utils.MIN_TEXT_LINES:
        texts_total += 1
        if link_no > start_link_idx:
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
        with open(text_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            print(header, file=f)
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
_utils.make_chunks(links_num)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(links_num, isdialog=False)
