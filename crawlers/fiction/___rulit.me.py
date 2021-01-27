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


SEED = 42
ROOT_URL = 'https://www.rulit.me'
INIT_URL = ROOT_URL + '/tag/samizdat/all/{}/date'

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Authors download
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]

else:
    links = OrderedDict()
    res = utils.get_url(INIT_URL.format(1))
    res = res.text
    pos = res.find('/date title="Последняя страница">')
    assert pos >= 0, "ERROR: Can't find authors on {}".format(url)
    res = res[:pos]
    pos = res.rfind('/')
    assert pos >= 0, "ERROR: Can't find authors on {}".format(url)
    max_page_no = int(res[pos + 1:])
    for page_no in range(1, max_page_no + 1):
        url = INIT_URL.format(page_no)
        res = utils.get_url(url)
        res = res.text
        res = res.split('<article class="single-blog post-list">')[1:]
        assert page_no == max_page_no or len(res) == 10, \
            'ERROR: Only {} books on {}'.format(len(res), url)
        for book in res:
            token = '<a href="'
            pos = book.find(token)
            book = book[pos + len(token):]
            pos = book.find('"')
            book_url = book[:pos]
            token = '<div class="book_info">Автор: <a href="'
            pos = book.find(token)
            book = book[pos + len(token):]
            pos = book.find('">')
            author_url = book[:pos]
            book = book[pos + 2:]
            pos = book.find('</a>')
            author_name = re.sub('<.*?>', '', book[:pos]).strip()
            token = '<div class="book_info">Язык: <span class="date_value">'
            pos = book.find(token)
            book = book[pos + len(token):]
            pos = book.find('<')
            lang = book[:pos]
            if lang == 'русский':
                links[book_url] = (author_url, author_name)
        print('\r{} (of {})'.format(page_no, max_page_no), end='')
    links = list('\t'.join([x, '\t'.join(y)]) for x, y in links.items())

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
    print()

links_, links = links, OrderedDict()
for link in links_:
    book_url, author_url, author_name = link.split('\t')
    if author_url in links:
        links[author_url].append(book_url)
    else:
        links[author_url] = [book_url]
num_links = len(links)
print(num_links)
exit()

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
    #header = unescape(header).replace('\u200b', '') \
    #                         .replace('\ufeff', '').strip()
    header = utils.norm_text2(header)
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
        #line = unescape(re1.sub('', line)).replace('\u200b', '') \
        #                                  .replace('\ufeff', '') \
        #                                  .replace('й', 'й') \
        #                                  .replace('ё', 'ё') \
        #                                  .strip()
        line = utils.norm_text2(re1.sub('', line))
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
