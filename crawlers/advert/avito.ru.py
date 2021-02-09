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
#637640 1612858924 30 30
#URL = ROOT_URL + '/lastreviews/{}/'
'''
COOKIES = {
    '__cfduid': 'd53060364c421f40d4bb516eddc509b281612858818',
    'buyer_laas_location': '637640',
    'buyer_local_priority_v2': '0',
    'buyer_location_id': '637640',
    'buyer_selected_search_radius4': '0_general',
    'dfp_group': '66',
    'f': '5.10a94bb89dd075604b5abdd419952845a68643d4d8df96e9a68643d4d8df96e9a68643d4d8df96e9a68643d4d8df96e94f9572e6986d0c624f9572e6986d0c624f9572e6986d0c62ba029cd346349f36c1e8912fd5a48d02c1e8912fd5a48d0246b8ae4e81acb9fa1a2a574992f83a9246b8ae4e81acb9fad99271d186dc1cd0e992ad2cc54b8aa8fbcd99d4b9f4cbda2157fc552fc064112de6947c9626acff915ac1de0d034112dc0d86d9e44006d81a2a574992f83a9246b8ae4e81acb9fae2415097439d404746b8ae4e81acb9fad99271d186dc1cd0b5b87f59517a23f2c772035eab81f5e1c772035eab81f5e1c772035eab81f5e1fb0fb526bb39450a143114829cf33ca7bed76bde8afb15d28e3a80a29e104a6c2c61f4550df136d822df23874cf735ffd6a90fb62fab5a15021dce8db01be7bf510cbb367c10574b83cf065b75e4d46e53bc326cd5f74c8ba12a61c8a29e59f7b94fd65f3f32b4e22ebf3cb6fd35a0ac0df103df0c26013a28a353c4323c7a3a140a384acbddd748cb826f1b0f1a3c963de19da9ed218fe23de19da9ed218fe2555de5d65c04a913e400aa21d50ae3851e84d92bdde8b2a6',
    'lastViewingTime': '1612858818943',
    'luri': 'moskva',
    'no-ssr': '1',
    'SEARCH_HISTORY_IDS': '4',
    'sessid': '6653f10991c7236c677fdc818379bcb2.1609918004',
    'showedStoryIds': '57-56-51-50-49-48-47-42-32',
    'so': '1609918004',
    'sx': 'H4sIAAAAAAACA1XNQY7DIAyF4buw7sIkBkxuA25CI09LJdJxlSp3H7roaGb99H%2FvZYYHWxrhNpwFgaRAa1y0ajPTy3ybySzrclF8xov2WSpBRakKUopUZjAnM5vJejtEDODscTJ4LTu3LNuG2LBn3SRh%2BCXjXlbf8teegFVECqu%2BXxlRmegv6QaCTs68brQ993tAKqid08oAUD%2BkT8lCTnb0QNnHMaCjcXa4YDg74DQ76zIv%2FN%2BO4Th%2BABYobNoDAQAA',
    'u': '2kcmdlxa.hc3c8d.aptu5qhg2ng0',
    'v': '1612858817'
}
'''
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
        TIMESTAMP, OFFSET = f.readline().strip().split(':')
        OFFSET = int(OFFSET)
        links = [x for x in f.read().split('\n') if x]
else:
    TIMESTAMP, OFFSET = int(time.time()), 0
    links = []

if len(links) < MAX_LINKS:
    driver = _utils.selenium_init()
    links = OrderedDict({x: 1 for x in links})
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
        #res = res.json()
        res = json.loads(res)
        if DUMP:
            with open('1111.txt', 'wt', encoding='utf-8') as f:
                pprint(res, stream=f)
        items = res.get('items')
        assert items, 'ERROR: No items on page "{}"!'.format(url)
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
    print()
exit()
'''===========================================================================
Texts download and parse
==========================================================================='''
REDO_TEXT = False if utils.get_file_list(utils.TEXTS_DIR,
                                         utils.TEXTS_FOR_SOURCE) else True

page_fns = utils.get_file_list(utils.PAGES_DIR, utils.TEXTS_FOR_SOURCE)
start_link_idx = int(os.path.split(sorted(page_fns)[-1])[-1]
                         .replace(utils.DATA_EXT, '')) \
                     if len(page_fns) > 0 else \
                 0
texts_total = 0

re0 = re.compile(r'\W|\d')
re1 = re.compile(r'[^ЁА-Яёа-я]')
re5 = re.compile(r'\W')
re10a = re.compile(r'<h1 class="largeHeader"><a href="[^"]+?"><span id="product-ttl-\d+" itemprop="name">([^<]+?)</span>')
re10 = re.compile(r'<h2 class="reviewTitle" itemprop="name">(?:\s|\n)*<a href=[^>]+>([^<]+?)</a>')
re11 = re.compile(r'<div class="description[^"]*" itemprop="reviewBody">((?:.|\n)+)$')
re12a = re.compile(r'<s>.*?</s>')
#re12b = re.compile(r'[^<>]+:\s*</p><blockquote>(?:.|\n)+?</blockquote>')
#re12b0 = re.compile(r'[^<>]+?:\s*</p><ul>(?:.|\n)+?</ul>')
re12b = re.compile(r'[^<>]+</p><blockquote>(?:.|\n)+?</blockquote>')
#re12b0 = re.compile(r'[^<>]+</p><ul>(?:.|\n)+?</ul>')
re12c = re.compile(r'<p[^>]*>((?:.|\n)+?)</p>')
re12c0 = re.compile(r'<li[^>]*>((?:.|\n)+?)</li>')
re12d = re.compile(r"<div class='inline[^>]+>[^<]*?</div>")
re12e = re.compile(r'<a [^>]>(.*?)</a>')
re12 = re.compile(r'<(?P<tag>\S+)[^>]*>(?:.|\n)*?</(?P=tag)>')
re13 = re.compile(r'<(?:[^/].*)?>')
need_enter = False
DUMP = False
for link_no, link in enumerate(links, start=1):
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    page_fn = utils.get_data_path(utils.PAGES_DIR,
                                  utils.TEXTS_FOR_SOURCE, link_no)
    text_fn = utils.get_data_path(utils.TEXTS_DIR,
                                  utils.TEXTS_FOR_SOURCE, link_no)
    page = None
    #link = 'https://irecommend.ru/content/venus-sensitive-s-5-lezviyami-i-ego-otlichie-ot-obychnykh-venus-foto-sravneniya-i-lichnoe-mn'
    #link = 'https://irecommend.ru/content/paletka-kotoraya-tait-v-sebe-syurprizy'
    #if link_no > start_link_idx:
#TODO:
    if not os.path.isfile(page_fn):
        if link_no <= start_link_idx and not REDO_TEXT:
            continue
###
        res = utils.get_url(link, headers=HEADERS, cookies=COOKIES)
        page = res.text
        with open(page_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            f.write(page)
        if DUMP:
            with open('1111.html', 'wt', encoding='utf-8') as f:
                f.write(page)
        if page.find('<title>Пожалуйста, войдите под своим именем пользователя') > 0 \
        or page.find('<h1 class="not-found-title">') > 0:
            continue
    else:
#TODO:
        if link_no <= start_link_idx and not REDO_TEXT:
            continue
###
        if not os.path.isfile(page_fn):
            continue
        if os.path.isfile(text_fn):
            texts_total += 1
            continue
        with open(page_fn, 'rt', encoding='utf-8') as f:
            link = f.readline().rstrip()
            page = f.read()
    match = re10a.search(page)
    assert match, "ERROR: Can't find header1 on page {}".format(link)
    header = utils.norm_text2(match.group(1))
    match = re10.search(page)
    assert match, "ERROR: Can't find header2 on page {}".format(link)
    header += '\n' + utils.norm_text2(match.group(1))
    match = re11.search(page)
    assert match, "ERROR: Can't find review on page {}".format(link)
    text = match.group(1)
    text = text.replace('\n', '').replace('<em>', '').replace('</em>', '') \
               .replace('<strong>', '').replace('</strong>', '')
    text = re12a.sub(' ', text)
    if DUMP:
        with open('12a.html', 'wt', encoding='utf-8') as f:
            f.write(text)
    text = re12b.sub('</p>', text).replace('<p></p>', '') \
                                  .replace('<ul>', '').replace('</ul>', '')
    #text = re12b0.sub('</p>', re12b.sub('</p>', text)).replace('<p></p>', '')
    if DUMP:
        with open('12b.html', 'wt', encoding='utf-8') as f:
            f.write(text)
    text = re12c.sub(r'\n\g<1>\n', re12c0.sub(r'\n\g<1>\n', text))
    if DUMP:
        with open('12c.html', 'wt', encoding='utf-8') as f:
            f.write(text)
    text = re12d.sub(r'\n', text)
    if DUMP:
        with open('12d.html', 'wt', encoding='utf-8') as f:
            f.write(text)
    text = re12e.sub(r'\g<1>', text)
    if DUMP:
        with open('12e.html', 'wt', encoding='utf-8') as f:
            f.write(text)
    text = re12.sub('', text).replace('<br>', '\n') \
                             .replace('<br/>', '\n').replace('<br />', '\n')
    if DUMP:
        with open('12.html', 'wt', encoding='utf-8') as f:
            f.write(text)
    text = re13.sub('', text)
    if DUMP:
        with open('13.html', 'wt', encoding='utf-8') as f:
            f.write(text)
    pos = text.find('<')  ## </div>
    if pos >= 0:
        text = text[:pos]
    text = utils.norm_text2(text)
    lines = [header] + [x for x in (x.strip() for x in text.split('\n')) if x]
    res, text = False, None
    while len(lines) >= _utils.MIN_TEXT_LINES:
        text = '\n'.join(lines)
        text0 = re0.sub('', text)
        text1 = re1.sub('', text0)
        if any(x in 'ЀЂЃЄЅІЇЈЉЊЋЌЍЎЏѐђѓєѕіїјљњћќѝўџѠѡѢѣѤѥѦѧѨѩѪѫѬѭѮѯѰѱѲѳѴѵѶѷѸѹ'
                    'ѺѻѼѽѾѿҀҁ҂҃҄҅҆҇҈҉ҊҋҌҍҎҏҐґҒғҔҕҖҗҘҙҚқҜҝҞҟҠҡҢңҤҥҦҧҨҩҪҫҬҭҮүҰұ'
                    'ҲҳҴҵҶҷҸҹҺһҼҽҾҿӀӁӂӃӄӅӆӇӈӉӊӋӌӍӎӏӐӑӒӓӔӕӖӗӘәӚӛӜӝӞӟӠӡӢӣӤӥӦӧӨө'
                    'ӪӫӬӭӮӯӰӱӲӳӴӵӶӷӸӹӺӻӼӽӾӿ' for x in text0):
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
    print('\r{} (of {})'.format(texts_total, utils.TEXTS_FOR_SOURCE), end='')
    need_enter = True
    #exit()
if need_enter:
    print()

'''===========================================================================
Chunks creation
==========================================================================='''
_utils.make_chunks(utils.TEXTS_FOR_SOURCE)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(utils.TEXTS_FOR_SOURCE, isdialog=False)
