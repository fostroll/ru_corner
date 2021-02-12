#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
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
ROOT_URL = 'https://www.avito.ru'
INIT_URL = ROOT_URL + '/web/1/main/items?forceLocation=false&locationId={}&lastStamp={}&limit=30&offset={}'
MAX_LINKS = utils.TEXTS_FOR_SOURCE * 10
SILENT = False
DUMP = True

if SEED:
    random.seed(SEED)

'''===========================================================================
Links download
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]
        if not links[0].startswith('http'):
            TIMESTAMP, OFFSET = links[0].split(':')
            OFFSET = int(OFFSET)
            links = links[1:]
else:
    TIMESTAMP, OFFSET = int(time.time()), 0
    links = []

if len(links) < MAX_LINKS:
    driver = _utils.selenium_init()
    links = OrderedDict({x: 1 for x in links})
    no_items = False
    while True:
        url = INIT_URL.format('', TIMESTAMP, OFFSET)
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
        res = json.loads(res)
        if DUMP:
            with open('1111.txt', 'wt', encoding='utf-8') as f:
                pprint(res, stream=f)
        items = res.get('items')
        assert items or not no_items, \
            'ERROR: No items on page "{}"!'.format(url)
        if not items:
            print('WARNING: No items. Reloading')
            no_items = True
            driver.quit()
            driver = _utils.selenium_init()
            continue
        no_items = False
        need_break = False
        for item_no, item in enumerate(items):
            link = item.get('urlPath')
            if not link:
                if 'bannerId' in item:
                    continue
                else:
                    with open('2222.txt', 'wt', encoding='utf-8') as f:
                        pprint(item, stream=f)
                    assert link, 'ERROR: No url on page "{}", item {}!' \
                                     .format(url, item_no)
            link = ROOT_URL + link
            if link in links:
                continue
            links[link] = 1
            if len(links) >= MAX_LINKS:
                need_break = True
                break
        OFFSET += item_no + 1
        with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
            print('{}:{}'.format(TIMESTAMP, OFFSET), file=f)
            f.write('\n'.join(links))
        print('\r{} (of {})'.format(len(links), MAX_LINKS), end='')
        if need_break:
            break
        time.sleep(5)
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
    if os.path.isfile(_utils.AUTHORS_IGNORE_FN):
        with open(_utils.AUTHORS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            authors_ignore = set(x for x in f.read().split('\n') if x)
    else:
        authors_ignore = set()
    driver = None
    for link_no, link in enumerate(links, start=1):
        if texts_total >= utils.TEXTS_FOR_SOURCE:
            break
        page_fn = utils.get_data_path(utils.PAGES_DIR, MAX_LINKS, link_no)
        text_fn = utils.get_data_path(utils.TEXTS_DIR, MAX_LINKS, link_no)
        page = None
        #link = 'https://www.avito.ru/moskva/sobaki/tsvergshnautser_schenki_2103162316'
        if link_no > start_link_idx:
            if not driver:
                driver = _utils.selenium_init()
            time.sleep(5)
            driver.get(link)
            page = driver.page_source
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
                f.write(page)
        if page.find('class="item-closed-warning"') > 0 \
        or page.find('<title>Ошибка 404') > 0:
            continue
        token = '<span class="title-info-title-text" itemprop="name">'
        pos = page.find(token)
        if pos < 0:
            print('WARNING: No author on page {} (a list?)"'.format(link))
            continue
        res = page[pos + len(token):]
        pos = res.find('<')
        header = utils.norm_text2(res[:pos])
        token = '<div class="item-description-text" itemprop="description">'
        pos = res.find(token)
        if pos < 0:
            token = '<div class="item-description-html" itemprop="description">'
            pos = res.find(token)
        assert pos > 0, "ERROR: Can't find text on page {}".format(link)
        res = res[pos + len(token):]
        pos = res.find('</div>')
        text = res[:pos]
        res = res[pos:]
        if DUMP:
            with open('1111.txt', 'wt', encoding='utf-8') as f:
                f.write(text)
        text = '\n'.join([x for i, x in enumerate(x for x in text.split('<p>')
                                                    for x in x.split('</p>'))
                            if i % 2])
        if DUMP:
            with open('1111.txt', 'at', encoding='utf-8') as f:
                print('\n---', file=f)
                f.write(text)
        text = utils.norm_text2(text.replace('<br>', '\n')
                                    .replace('<br/>', '\n')
                                    .replace('<br />', '\n')) \
                    .replace('<strong>', '').replace('</strong>', '')  # workaround (just 1 case, but effective)
        if DUMP:
            with open('1111.txt', 'at', encoding='utf-8') as f:
                print('\n---', file=f)
                f.write(text)
        token = 'https://www.avito.ru/user/'
        pos = res.find('https://www.avito.ru/user/')
        if pos < 0:
            print('WARNING: No author on page {} (a shop/resume?)'
                      .format(link))
            continue
        res = res[pos + len(token):]
        pos = res.find('/')
        author = res[:pos]
        if author in authors_ignore:
            continue
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
        authors_ignore.add(author)
        with open(_utils.AUTHORS_IGNORE_FN, 'wt', encoding='utf-8') as f:
            f.write('\n'.join(authors_ignore))
        with open(text_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            f.write(text)
        print('\r{} (of {})'.format(texts_total, utils.TEXTS_FOR_SOURCE),
              end='')
        need_enter = True
        #exit()
    if driver:
        driver.quit()
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
