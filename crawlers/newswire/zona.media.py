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
ROOT_URL = 'https://zona.media'
URL = ROOT_URL + '/news'

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Links download
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]

else:
    links = OrderedDict()
    re0 = re.compile(r'<a href="([^">]+)"[^>]*>.*?<header[^>]*>([^<]+)'
                     r'</header></a>')
    res = utils.get_url(URL)
    page = res.text
    res = re.search('<a href="(/_load\?selector=news'
                    '&amp;page=0&amp;total=\d+)', page)
    assert res, 'ERROR: next link have not found on the main page'
    url = res.group(1)
    while url and len(links) < utils.TEXTS_FOR_SOURCE * 2:
        res = utils.get_url(ROOT_URL + unescape(url))
        res = res.json()
        data = res.get('data')
        assert data, 'ERROR: no data on the link ' + url
        for datum in data:
            datum = datum.get('html')
            datum = re0.findall(unescape(datum))
            for link, header in datum:
                links[ROOT_URL + link] = \
                    unescape(header).strip().replace('\u2011', '-')
        print('\r{}'.format(len(links)), end='')
        url = res.get('link', {}).get('url')
    links = list('\t'.join(x) for x in links.items())

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
    print()

num_links = len(links)

'''===========================================================================
Texts download and parse
==========================================================================='''
page_fns = utils.get_file_list(utils.PAGES_DIR, num_links)
start_link_idx = int(os.path.split(sorted(page_fns)[-1])[-1]
                         .replace(utils.DATA_EXT, '')) \
                     if len(page_fns) > 0 else \
                 0
texts_total = 0

re0 = re.compile(r'<p>((?:.|\n)*?)</p>')
re1 = re.compile(r'<.*?>')
need_enter = False
for link_no, link in enumerate(links, start=1):
    link, header = link.split('\t')
    header = unescape(header).replace('\u200b', '') \
                             .replace('\ufeff', '').strip()
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    #link = 'https://www.interfax.ru/interview/374150'
    page_fn = utils.get_data_path(utils.PAGES_DIR, num_links, link_no)
    text_fn = utils.get_data_path(utils.TEXTS_DIR, num_links, link_no)
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
    res = re0.findall(page)
    lines = []
    for line in res:
        line = line.replace('\u200b', '').replace('\ufeff', '').strip()
        if line.startswith('<b>Исправлено'):
            break
        line = unescape(re1.sub('', line)).strip()
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
                                    min(utils.TEXTS_FOR_SOURCE, num_links)),
              end='')
        need_enter = True
    #exit()
if need_enter:
    print()

'''===========================================================================
Chunks creation
==========================================================================='''
_utils.make_chunks(num_links)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(num_links, isdialog=False)
