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
ROOT_URL = 'https://www.tatler.ru'
URL = ROOT_URL + '/news/'
URL_1 = 'https://api.tatler.ru/article/list?_limit={}&_offset={}' \
        '&_order_dir=DESC&_order_by=publishedAt&tags=1968'

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
    batch, shift = 100, 0
    while len(links) < utils.TEXTS_FOR_SOURCE * 2:
        url = URL_1.format(batch, shift)
        res = utils.get_url(url)
        res = res.json()
        assert res, 'ERROR: no items on the link ' + url
        for item_no, item in enumerate(res):
            name = item.get('name')
            assert name, \
                'ERROR: cannot find a name in the record #{} of page {}' \
                    .format(item_no, url)
            slug = item.get('slug')
            assert slug, \
                'ERROR: cannot find a slug in the record #{} of page {}' \
                    .format(item_no, url)
            links[URL + slug] = unescape(name.replace('_', '')).strip()
        print('\r{}'.format(len(links)), end='')
        shift += batch
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

re0 = re.compile(r'<div class="article__text">((?:.|\n)*?)</div>')
re1 = re.compile(r'<p>((?:.|\n)*?)</p>')
re2 = re.compile(r'<.*?>|\(.*?\)')
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
    res = re0.search(page)
    assert res, 'ERROR: no article on the page {}'.format(url)
    res = res.group(1)
    res = re1.findall(res)
    lines = []
    for line in res:
        line = line.strip()
        if (line.startswith('<em>') and line.endswith('</em>')) \
        or line.startswith('<strong>Смотрите и&nbsp;читайте Tatler там, где вам удобно:'):
            break
        line = unescape(re2.sub('', line)).strip()
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
