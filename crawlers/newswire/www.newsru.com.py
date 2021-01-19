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
ROOT_URL = 'https://www.newsru.com'
URL = ROOT_URL + '/allnews/'

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
    re0 = re.compile(r'<a href="([^"]+)" class="index-news-title">\s*\n?'
                     r'\s*([^<]+)\s*\n?\s*</a>')
    re1 = re.compile(r'<a class="arch-arrows-link-l" href="([^"]+)"')
    url = URL
    while len(links) < utils.TEXTS_FOR_SOURCE * 2:
        res = utils.get_url(url)
        page = unescape(res.text)
        res = re0.findall(page)
        assert res, 'ERROR: no articles on the page {}'.format(url)
        for link, header in res:
            if link.startswith('/') and not link.startswith('/blog'):
                links[ROOT_URL + link] = unescape(header).strip()
        print('\r{}'.format(len(links)), end='')
        res = re1.search(page)
        assert res, 'ERROR: no prev link on the page {}'.format(url)
        url = ROOT_URL + res.group(1)
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
re1 = re.compile(r'<blockquote.*</blockquote>')
re2 = re.compile(r'<a  class="part-link".*</a>')
re3 = re.compile(r'<.*?>')
need_enter = False
for link_no, link in enumerate(links, start=1):
    link, header = link.split('\t')
    #header = unescape(header).replace('\u200b', '').replace('\ufeff', '') \
    #                         .replace('й', 'й').replace('ё', 'ё').strip()
    header = utils.norm_text2(header)
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    #link = 'https://www.newsru.com/sport/11oct2020/ukrger.html'
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
    res = re0.search(page)
    assert res, 'ERROR: no article on the page {}'.format(url)
    res = res.group(1).split('<p class="maintext">')
    lines = []
    for line in res:
        #line = unescape(re3.sub('', re2.sub('', re1.sub('', line)))) \
        #           .replace('\u200b', '').replace('\ufeff', '').strip()
        line = utils.norm_text2(re3.sub('', re2.sub('', re1.sub('', line))))
        if any(x.isalpha() for x in line):
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
