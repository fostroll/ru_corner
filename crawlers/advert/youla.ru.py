#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import itertools
import json
import os
from pprint import pprint
import random
import re
import time

###
import sys
sys.path.append('../')
###
import utils
import _utils


SEED = 42
ROOT_URL = 'https://youla.ru'
INIT_URL = 'https://api.youla.io/api/v1/products?app_id=web/2&uid=602245c3ce39c&timestamp={}&page={}&limit=60&features=banners,serp_id,boosts&view_type=tile&search_id='
#URL = ROOT_URL + '/lastreviews/{}/'
MAX_LINKS = utils.TEXTS_FOR_SOURCE * 2
SILENT = False
DUMP = False

if SEED:
    random.seed(SEED)

'''===========================================================================
Links download
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        #TIMESTAMP = f.readline().strip()
        links = [x for x in f.read().split('\n') if x]
else:
    #TIMESTAMP = int(time.time())
    links = []

if len(links) < MAX_LINKS:
    driver = _utils.selenium_init(silent=True)
    links = OrderedDict({x: 1 for x in links})
    if os.path.isfile(_utils.AUTHORS_IGNORE_FN):
        with open(_utils.AUTHORS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            authors_ignore = set(x for x in f.read().split('\n') if x)
    else:
        authors_ignore = set()
    need_break = False
    while True:
        for page_no in itertools.count(1):
            #url = INIT_URL.format(TIMESTAMP, page_no)
            url = INIT_URL.format('', page_no)
            if not SILENT:
                print(url)
            driver.get(url)
            res = driver.page_source
            if DUMP:
                with open('1111.html', 'wt', encoding='utf-8') as f:
                    f.write(res)
            pos = res.find('{')
            assert pos >= 0, 'ERROR: No json start on page "{}"!'.format(url)
            res = res[pos:]
            pos = res.rfind('}')
            assert pos >= 0, 'ERROR: No json end on page "{}"!'.format(url)
            res = res[:pos + 1]
            #res = res.json()
            res = json.loads(res)
            if DUMP:
                with open('1111.txt', 'wt', encoding='utf-8') as f:
                    pprint(res, stream=f)
            items = res.get('data')
            if not items:
                print('WARNING: No more items on page "{}"!'.format(url))
                #driver.quit()
                break
            for item_no, item in enumerate(items):
                link = item.get('url')
                if not link:
                    with open('2222.txt', 'wt', encoding='utf-8') as f:
                        pprint(item, stream=f)
                    assert link, 'ERROR: No url on page "{}", item {}!' \
                                     .format(url, item_no)
                link = ROOT_URL + link
                if link in links:
                    continue
                author = item.get('owner', {}).get('id')
                if not author:
                    with open('2222.txt', 'wt', encoding='utf-8') as f:
                        pprint(item, stream=f)
                    assert author, 'ERROR: No owner on page "{}", item {}!' \
                                       .format(url, item_no)
                if author in authors_ignore:
                    continue
                authors_ignore.add(author)
                links[link] = 1
                if len(links) >= MAX_LINKS:
                    need_break = True
                    break
            with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
                #print(TIMESTAMP, file=f)
                f.write('\n'.join(links))
            with open(_utils.AUTHORS_IGNORE_FN, 'wt', encoding='utf-8') as f:
                f.write('\n'.join(authors_ignore))
            print('\r{} (of {})'.format(len(links), MAX_LINKS), end='')
            if need_break:
                break
        if need_break:
            break
        time.sleep(3600)
    links = list(links)
    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
    driver.quit()
    print()

'''===========================================================================
Texts download and parse
==========================================================================='''
if len(utils.get_file_list(utils.TEXTS_DIR,
                           MAX_LINKS)) < utils.TEXTS_FOR_SOURCE:
    page_fns = utils.get_file_list(utils.PAGES_DIR, MAX_LINKS)
    start_link_idx = int(os.path.split(sorted(page_fns)[-1])[-1]
                             .replace(utils.DATA_EXT, '')) \
                         if len(page_fns) > 0 else \
                     0
    texts_total = 0

    re0 = re.compile(r'\W|\d')
    re1 = re.compile(r'[^ЁА-Яёа-я]')
    re5 = re.compile(r'\W')
    need_enter = False
    DUMP = True
    for link_no, link in enumerate(links, start=1):
        if texts_total >= utils.TEXTS_FOR_SOURCE:
            break
        page_fn = utils.get_data_path(utils.PAGES_DIR, MAX_LINKS, link_no)
        text_fn = utils.get_data_path(utils.TEXTS_DIR, MAX_LINKS, link_no)
        page = None
        #link = 'https://youla.ru/domodedovo/hobbi-razvlecheniya/nastolnye-igry/nastolnaia-ighra-volshiebnaia-chietvierka-5ee735285758bd443e3f83c3'
        if link_no > start_link_idx:
            time.sleep(1)
            res = utils.get_url(link)
            page = res.text
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
        else:
            if not os.path.isfile(page_fn):
                continue
            if os.path.isfile(text_fn):
                texts_total += 1
                continue
            with open(page_fn, 'rt', encoding='utf-8') as f:
                link = f.readline().rstrip()
                page = f.read()
        if DUMP:
            with open('1111.html', 'wt', encoding='utf-8') as f:
                print(link, file=f)
        if page.find('<h1 class="error_page__title">404</h1>') > 0 \
        or page.find('<title>Удалено</title>') > 0 \
        or page.find('<title>Заблокировано</title>') > 0:
            continue
        token = 'window.__YOULA_STATE__ = '
        pos = page.find(token)
        if pos < 0:
            print('WARNING: No state on page {}'.format(link))
            continue
        res = page[pos + len(token):]
        pos = res.find('\n')
        res = res[:pos].strip()
        assert res.endswith(';'), \
               'ERROR: No state end on page {}'.format(link)
        res = res[:-1]
        if DUMP:
            with open('1111.json', 'wt', encoding='utf-8') as f:
                f.write(res)
        state = json.loads(res)
        if DUMP:
            from pprint import pprint
            with open('1111.json', 'wt', encoding='utf-8') as f:
                pprint(state, stream=f)
        products = state.get('entities', {}).get('products')
        assert products, 'ERROR: No products in state on page {}'.format(link)
        product = products[0]
        header = utils.norm_text2(product['name'])
        text = utils.norm_text2(product['description'])
        if DUMP:
            with open('1111.txt', 'at', encoding='utf-8') as f:
                f.write(text)
        lines = [header] + [x for x in (x.strip() for x in text.split('\n'))
                              if x]
        res, text = False, None
        while len(lines) >= _utils.MIN_TEXT_LINES:
            text = '\n'.join(lines)
            text0 = re0.sub('', text)
            text1 = re1.sub('', text0)
            if any(x in 'ЀЂЃЄЅІЇЈЉЊЋЌЍЎЏѐђѓєѕіїјљњћќѝўџѠѡѢѣѤѥѦѧѨѩѪѫѬѭѮѯѰѱѲѳѴѵ'
                        'ѶѷѸѹѺѻѼѽѾѿҀҁ҂҃҄҅҆҇҈҉ҊҋҌҍҎҏҐґҒғҔҕҖҗҘҙҚқҜҝҞҟҠҡҢңҤҥҦҧҨҩ'
                        'ҪҫҬҭҮүҰұҲҳҴҵҶҷҸҹҺһҼҽҾҿӀӁӂӃӄӅӆӇӈӉӊӋӌӍӎӏӐӑӒӓӔӕӖӗӘәӚӛӜӝ'
                        'ӞӟӠӡӢӣӤӥӦӧӨөӪӫӬӭӮӯӰӱӲӳӴӵӶӷӸӹӺӻӼӽӾӿ' for x in text0):
                if not SILENT:
                    print('{}: non-Russian'.format(link_no))
                text = None
                break
            if text0 and len(text1) / len(text0) >= .9:
                num_words = len([x for x in text.split()
                                   if re5.sub('', x)])
                #print(num_words)
                if num_words > _utils.MAX_CHUNK_WORDS:
                    lines = lines[:-1]
                    continue
                if num_words >= _utils.MIN_CHUNK_WORDS:
                    res = True
            else:
                if not SILENT:
                    print('{}: non-Cyrillic'.format(link_no))
                text = None
            break
        if not res:
            if not SILENT:
                if not text:
                    print('no text')
                    #if nop:
                    #    exit()
                else:
                    print('text beyond limits:')
                    print(text)
            continue
        texts_total += 1
        with open(text_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            f.write(text)
        print('\r{} (of {})'.format(texts_total, utils.TEXTS_FOR_SOURCE),
              end='')
        need_enter = True
        #exit()
    if need_enter:
        print()

'''===========================================================================
Chunks creation
==========================================================================='''
_utils.make_chunks(MAX_LINKS)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(MAX_LINKS, isdialog=False)
