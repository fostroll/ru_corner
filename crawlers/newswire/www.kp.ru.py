#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
from html import unescape
import itertools
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
ROOT_URL = 'https://www.kp.ru'
URL = ROOT_URL + '/online/'
URL_1 = ROOT_URL + '/content/api/1/pages/get.json/result/' \
                   '?pages.direction=page&pages.number={}' \
                   '&pages.spot=0&pages.target.class=100' \
                   '&pages.target.id=0'

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
    for page_no in itertools.count(1):
        url = URL_1.format(page_no)
        res = utils.get_url(url)
        res = res.json()
        childs = res.get('childs')
        assert childs, 'ERROR: no childs on the link ' + url
        for child_no, child in enumerate(childs):
            id_ = child.get('@id')
            title = child.get('ru', {}).get('title')
            assert id_ and title, \
                'ERROR: invalid format of the record #{} of page {}' \
                    .format(child_no, url)
            links['{}news/{}'.format(URL, id_)] = unescape(title).strip()
        print('\r{}'.format(len(links)), end='')
        if len(links) >= utils.TEXTS_FOR_SOURCE * 2:
            break
    links = list('\t'.join(x) for x in links.items())

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
    print()

num_links = len(links)

'''===========================================================================
Texts download and parse
==========================================================================='''
pages_fns = utils.get_file_list(utils.PAGES_DIR, num_links)
start_link_idx = int(os.path.split(sorted(pages_fns)[-1])[-1]
                         .replace(utils.DATA_EXT, '')) \
                     if len(pages_fns) > 0 else \
                 0
texts_total = 0

re0 = re.compile(r'<p class="styled__Paragraph-[^">]+">((?:.|\n)*?)</p>')
re1 = re.compile(r'<.*?>')
need_enter = False
for link_no, link in enumerate(links, start=1):
    link, header = link.split('\t')
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    #link = 'https://www.interfax.ru/interview/374150'
    page_fn = utils.get_data_path(utils.PAGES_DIR, num_links, link_no)
    text_fn = utils.get_data_path(utils.TEXTS_DIR, num_links, link_no)
    page = None
    if link_no > start_link_idx:
        res = utils.get_url(link)
        page = res = res.text
    else:
        if not os.path.isfile(page_fn):
            continue
        if os.path.isfile(text_fn):
            texts_total += 1
            continue
        with open(page_fn, 'rt', encoding='utf-8') as f:
            link = f.readline().rstrip()
            page = res = f.read()
    pos = res.find('<p class="styled__Paragraph-')
    if pos > 0:
        res = page[pos:]
    pos = res.find('</div>')
    if pos > 0:
        res = res[:pos]
    res = re0.findall(page)
    if not res:
        continue
    lines = []
    for line in res:
        line = unescape(re1.sub('', line)).strip()
        #if line in ['ЕЩЕ ПО ТЕМЕ', 'МЕЖДУ ТЕМ', 'ПО ТЕМЕ', 'ЧИТАЙТЕ ТАКЖЕ']:
        if len(line) > 5 and line.isupper() \
                         and line.replace(' ', '').isalpha():
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
