#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
from html import unescape
import itertools
import json
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
URL_1 = 'https://tgram.ru/wiki/stickers/channel_PersonActionsPagedSorted.php?action=list&jtStartIndex={}&jtPageSize=50&jtSorting=pp%20DESC'
URL_2 = 'https://xn--r1a.website/s/{}?before={}'

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
    for page_no in itertools.count():
        url = URL_1.format(page_no * 50)
        res = utils.get_url(url)
        res = res.json()
        max_link_no = res.get('TotalRecordCount')
        childs = res.get('Records')
        if len(childs) == 0:
            break
        for child_no, child in enumerate(childs):
            id_, name = child.get('id'), child.get('Name')
            assert id_, \
                'ERROR: invalid format of the record #{} of page {}' \
                    .format(child_no, url)
            links[id_] = unescape(name).strip()
        print('\r{} (of {})'.format(len(links), max_link_no), end='')

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

if texts_total < utils.TEXTS_FOR_SOURCE:
    need_enter = False
    driver = None
    for link_no, link in enumerate(links, start=1):
        if texts_total >= utils.TEXTS_FOR_SOURCE:
            break
        link = link.split()[0]
        #link = 'kinovinchik'
        page_fn = utils.get_data_path(utils.PAGES_DIR,
                                      num_links, link_no)
        text_fn = utils.get_data_path(utils.TEXTS_DIR,
                                      num_links, link_no)
        text, page = None, None
        if link_no > start_link_idx:
            res = utils.get_url(URL_2.format(link, '')).text
            with open(utils.get_data_path(utils.PAGES_DIR, num_links, link_no) + '.txt', 'wt', encoding='utf-8') as f:
                f.write(res)
                print('\n{}'.format(link), file=f)
            while True:
                pos = res.find('<div class="tgme_widget_message js-widget_message" data-post=')
                if pos < 0:
                    break
                res = res[pos:]
                pos = res.find('</time>')
                msg = res[:pos]
                text = re.search(
                    '<div class=".*?js-message_text.*?".*?>(.+?)</div>', msg
                )
                if text:
                    text = unescape(re.sub(r'<[^>]*>', ' ', text.group(1)))
                    text = text.replace('\u200b', '').replace('\ufeff', '') \
                               .replace('й', 'й').replace('ё', 'ё').strip()
                    text0 = re.sub(r'\W|\d', '', re.sub(r'#\b\S+\b', '',
                                                        text))
                    text1 = re.sub(r'[^ЁА-Яёа-я]', '', text0)
                    if text0 and len(text1) / len(text0) >= .9:
                        num_words = len([x for x in re.sub(r'#\b\S+\b', '',
                                                           text).split()
                                           if re.sub(r'\W', '', x)])
                        if num_words >= _utils.MIN_CHUNK_WORDS \
                       and num_words <= _utils.MAX_CHUNK_WORDS:
                            page = msg
                            break
                res = res[1:]
        else:
            if not os.path.isfile(page_fn):
                continue
            if os.path.isfile(text_fn):
                texts_total += 1
                continue
            with open(page_fn, 'rt', encoding='utf-8') as f:
                link = f.readline().rstrip()
                page = f.read()
        if page:
            text = re.search(
                '<div class=".*?js-message_text.*?".*?>(.+?)</div>',
                page
            )
            text = text.group(1) \
                       .replace('\n', ' ').replace('<br>', '\n') \
                       .replace('<br/>', '\n').replace('<br />', '\n').strip()
            if text.endswith('</a>'):
                pos = text.rfind('<a')
                text = text[:pos]
            #text = unescape(re.sub(r'<[^>]*>', '', text))
            #text = text.replace('\u200b', '').replace('\ufeff', '') \
            #           .replace('й', 'й').replace('ё', 'ё')
            text = utils.norm_text2(re.sub(r'<[^>]*>', '', text))
            text = re.sub(r'[^\S\n]+', ' ', text)
            text = '\n'.join(x for x in (x.strip() for x in text.split('\n'))
                               if x)
            texts_total += 1
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
            with open(text_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(text)
            print('\r{} (of {})'.format(texts_total,
                                        min(utils.TEXTS_FOR_SOURCE,
                                            num_links)),
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
