#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import os
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
ROOT_URL = 'https://irecommend.ru'
INIT_URL = ROOT_URL + '/mainpage_json/2aa7fd3048c6c2a21c190e5c911ba154/{}/new?pages={}&_={}'
URL = ROOT_URL + '/lastreviews/{}/'
COOKIES = {
    'ab_var': '7',
    'ss_uid': '16127689059357592',
    'stats_s_a': '5yCWdE3qKpSukMFxtXnHmRdpqnhedr%2FgdxiGEyUzvhJy9IMakAA1QAIUJJmDZ1qw',
    'stats_u_a': 'fko5IxLNzat9avMj9v1UDtc%2FaNsBQ9K%2F7bgS3UyoDyQxVgRqM9UZj1fkEHoCwRfjoIGOB0J0vA68i3JY9db6LrfNh6VCLOvq',
    'statsactivity': '5',
    'statstimer': '4'
}
SILENT = False

if SEED:
    random.seed(SEED)

'''===========================================================================
Links download
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]
else:
    links = []

if len(links) < utils.TEXTS_FOR_SOURCE:
#if len(links) < 1:
    links = OrderedDict({x: 1 for x in links})
    if os.path.isfile(_utils.AUTHORS_IGNORE_FN):
        with open(_utils.AUTHORS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            authors_ignore = set(x for x in f.read().split('\n') if x)
    else:
        authors_ignore = set()
    MAX_LINKS = utils.TEXTS_FOR_SOURCE * 2
    offset = 0
    while True:
        url = INIT_URL.format(offset, 1, time.time_ns() // 1000000)
        res = utils.get_url(url, headers=_utils.HEADERS, cookies=COOKIES)
        res = res.json()
        offset = res['offset']
        output = res['output']
        with open('1111.html', 'wt', encoding='utf-8') as f:
            f.write(output)
        if not output:
            break
        res = output.split('<div class="smTeaser')[1:]
        res_len = len(res)
        if res_len != 20:
            assert res_len, 'ERROR: No links on page "{}"!'.format(url)
            print('WARNING: {} links on page "{}" (must be 20)'
                      .format(res_len, url))
        need_break = False
        for rec_no, rec in enumerate(res):
            token = '<a class="productPhoto" href="'
            pos = rec.find(token)
            assert pos >= 0, "ERROR: Can't find product on {}, record {}" \
                                 .format(url, rec_no)
            product = rec = rec[pos + len(token):]
            pos = product.find('"')
            assert pos >= 0, "ERROR: Can't find product on {}, record {}" \
                                 .format(url, rec_no)
            product = product[:pos]
            link = '{}{}'.format(ROOT_URL, product)
            if link in links:
                continue
            token = '<div class="authorName"><a href="/users/'
            pos = rec.find(token)
            assert pos >= 0, "ERROR: Can't find user on {}, record {}" \
                                 .format(url, rec_no)
            author = rec[pos + len(token):]
            pos = author.find('"')
            assert pos >= 0, "ERROR: Can't find user on {}, record {}" \
                                 .format(url, rec_no)
            author = author[:pos]
            if author in authors_ignore:
                continue
            authors_ignore.add(author)
            links[link] = 1
            if len(links) >= MAX_LINKS:
                need_break = True
                break
        print('\r{} (of {})'.format(len(links), MAX_LINKS), end='')
        if need_break:
            break
    with open(_utils.AUTHORS_IGNORE_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(authors_ignore))
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
