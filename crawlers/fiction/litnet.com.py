#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
from junky import seconds_to_strtime
from html import unescape
import os
import random
import re
import time

###
import sys
sys.path.append('../')
###
import utils


SEED = 42
ROOT_URL = 'https://litnet.com'
INIT_URL = ROOT_URL + '/ru/top/all?alias=all&page={}'
MIN_TEXT_LINES = 1
MAX_TEXT_LINES = 10
MIN_CHUNK_WORDS = 40
MAX_CHUNK_WORDS = 200
SILENT = True
INVALID_URLS = set(
#    '/ru/book/medved-i-zayac-b37435'
)

if SEED:
    random.seed(SEED)

cookies = {
 '_identity': '9fb5418dfd92e88d65fb7ebc8a2fac16fb8ec37179ba0938cfaece7254437b5ea%3A2%3A%7Bi%3A0%3Bs%3A9%3A%22_identity%22%3Bi%3A1%3Bs%3A52%3A%22%5B7609133%2C%22c4d639835c47559765e93052e983f64a%22%2C2592000%5D%22%3B%7D'
}

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
    token = '<li class="last"><a href="/ru/top/all?alias=all&amp;page='
    pos = res.find(token)
    assert pos >= 0, "ERROR: Can't find authors on {}".format(url)
    res = res[pos + len(token):]
    pos = res.find('"')
    assert pos >= 0, "ERROR: Can't find authors on {}".format(url)
    max_page_no = int(res[:pos])
    time0 = time.time()
    for page_no in range(1, max_page_no + 1):
        url = INIT_URL.format(page_no)
        res = utils.get_url(url)
        res = res.text
        res = res.split('<div class="book-img">')[1:]
        if page_no != max_page_no and len(res) != 20:
            print('\nWARNING: Only {} books on {}'.format(len(res), url))
        for book in res:
            token = '<h4 class="book-title"><a href="'
            pos = book.find(token)
            book = book[pos + len(token):]
            pos = book.find('"')
            book_url = book[:pos]
            token = '<a class="author" href="'
            pos = book.find(token)
            book = book[pos + len(token):]
            pos = book.find('">')
            author_url = book[:pos]
            book = book[pos + 2:]
            pos = book.find('<')
            author_name = book[:pos].strip()
            links[book_url] = (author_url, author_name)
        time1 = time.time()
        eta = (time1 - time0) * (max_page_no + 1 - page_no) / page_no
        print('\r', ' ' * 60, end='')
        print('\r{} (of {}); ETA: {}'
                  .format(page_no, max_page_no,
                          seconds_to_strtime(eta)),
              end='')
    links = list('\t'.join([x, '\t'.join(y)]) for x, y in links.items())

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
    time1 = time.time()
    print('\nTotal time:', seconds_to_strtime(time1 - time0))

links_, links = links, OrderedDict()
for link in links_:
    book_url, author_url, author_name = link.split('\t')
    if author_url in links:
        links[author_url].append(book_url)
    else:
        links[author_url] = [book_url]
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

re0 = re.compile(r'\W|\d')
re1 = re.compile(r'[^ЁА-Яёа-я]')
re3 = re.compile(r'<img .+?>')
re5 = re.compile(r'\W')
re10 = re.compile(r'<h1 class="roboto">(.+?)</h1>(?:.|\n)+?'
                  r'<a class="author" href=".+?">(.+?)</a>(?:.|\n)+?'
                  r'<div class="book-buttons">(?:.|\n)+?'
                  r'<a.+?" href="(/ru/reader/.+?)"')
re11 = re.compile(r'<select class=".+?" name="chapter">(?:.|\n)+?'
                  r'<option value="((?:.|\n)+)</select>')
re20 = re.compile(r'\d+(\..*)?$')
re21 = re.compile(r'\([cCсС]\)')
re22 = re.compile(r'\w$')
re23 = re.compile(r'\w')
re30 = re.compile(r'<(?P<tag>\S+) [^>]+display:none[^>]+>.*?</(?P=tag)>')
re31 = re.compile(r'</?(?:span|font).*?>')
re32 = re.compile(r'<s>.*?</s>')
need_enter = False
time0, eta, start_texts_total = None, None, 0
for link_no, (author_url, book_urls) in enumerate(links.items(), start=1):
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    page_fn = utils.get_data_path(utils.PAGES_DIR, num_links, link_no)
    text_fn = utils.get_data_path(utils.TEXTS_DIR, num_links, link_no)
    page = link = None
    if link_no > start_link_idx:
        if not time0:
            time0 = time.time()
            start_texts_total = texts_total
        for book_url_ in book_urls:
            #book_url_ = '/ru/book/zarisovka-nag-i-devica-b98035'
            if book_url_ in INVALID_URLS:
                continue
            for _ in range(3):
                book_url = ROOT_URL + book_url_
                #book_url = 'https://litnet.com/ru/book/medved-i-zayac-b37435'
                if not SILENT:
                    print(link_no, book_url)
                res = utils.get_url(book_url, cookies=cookies)
                res = res.text
                if not SILENT:
                    with open('1111.html', 'wt', encoding='utf-8') as f:
                        print(res, file=f)
                match = re10.search(res)
                if not match:
                    if res.find('<h2>Запрашиваемая страница '
                                 'не найдена</h2>') >= 0:
                        if not SILENT:
                            print('not found; retry')
                        need_retry = True
                        time.sleep(3)
                        continue
                    else:
                        if not SILENT:
                            print('document possible removed')
                        break
                book, author, book_url = match.groups()
                book_url = ROOT_URL + book_url
                #book_url = 'https://litnet.com/ru/reader/kosmos-yuli-chaikinoi-b79691?c=660003'
                if not SILENT:
                    print(link_no, book_url)
                res = utils.get_url(book_url, cookies=cookies)
                res = res.text
                if not SILENT:
                    with open('1111.html', 'wt', encoding='utf-8') as f:
                        print(res, file=f)
                assert res.find('<h1 class="adult-heading roboto">18\+</h1>') < 0, \
                    'ERROR: Unauthorized access. Update cookie!'
                match = re11.search(res)
                chapters = match.group(1).split('<option value="') if match else \
                           [None]
                if len(chapters) > 2:
                    chapters_ = chapters[1:-1]
                    random.shuffle(chapters_)
                    chapters = chapters_ + [chapters[0], chapters[-1]]
                book_url0 = book_url
                pos = book_url0.find('?')
                if pos > 0:
                    book_url0 = book_url0[:pos]
                need_retry = False
                for chapter in chapters:
                    if chapter:
                        pos = chapter.find('"')
                        chapter = chapter[:pos]
                        link = book_url0 + '?c={}'.format(chapter)
                        #link = 'https://litnet.com/ru/reader/medved-i-zayac-b37435'
                        if not SILENT:
                            print(link)
                        res = utils.get_url(link, cookies=cookies)
                        res = res.text
                    else:
                        link = book_url
                    res = re3.sub('', res).strip()
                    if not res:
                        continue
                    if not SILENT:
                        with open('1111.html', 'wt', encoding='utf-8') as f:
                            print(res, file=f)
                    if res.find('<div class="content chapter_paid">') > 0:
                        if not SILENT:
                            print('paid')
                        continue
                    pos = res.find('<div class="reader-text')
                    if pos < 0:
                        if res.find('<h2>Запрашиваемая страница '
                                     'не найдена</h2>') >= 0:
                            if not SILENT:
                                print('not found; retry')
                            need_retry = True
                            time.sleep(3)
                            break
                    res = res[pos:]
                    pos = res.find('</div>')
                    page = res[:pos]
                    break
                else:
                    print('\nWARNING: No text on {}'.format(book_url))
                    break
                if need_retry:
                    continue
                break
            if page:
                break
        else:
            continue
    else:
        if not os.path.isfile(page_fn):
            continue
        if os.path.isfile(text_fn):
            texts_total += 1
            continue
        with open(page_fn, 'rt', encoding='utf-8') as f:
            link = f.readline().rstrip()
            page = f.read()
    res, lines = page, []
    isbold = False
    # workarounds:
    res = re.sub('<p [^>]+</p>', '', res)
    res = re.sub('<a [^>]*href="#[^>"]*"[^>]*>[^<]*</a>', '', res)
    res = re.sub('<!--.*?-->', '', res)
    is_invalid = False
    while True:
        end_token = '</p>'
        pos = res.find('<p')
        nop = False
        if pos < 0:
            pos = res.find('<dd')
            if pos >= 0:
                end_token = '<dd'
            else:
                if not SILENT:
                    nop = True
                    print('no <p>')
                    with open('2222.html', 'wt', encoding='utf-8') as f:
                        print(res, file=f)
                        print('===', file=f)
                        print(lines, file=f)
                    #exit()
                break
        res = res[pos:]
        pos = res.find('>')
        attr = res[:pos]
        res = res[pos + 1:]
        pos = res.find(end_token)
        lines_ = res[:pos] if pos >= 0 else res
        if 'right' in attr or 'center' in attr:
            continue
        lines_ = [x for x in lines_.split('<br />') for x in x.split('<br>')]
        for line_no, line in enumerate(lines_):
            if not utils.norm_text2(line):
                continue
            #print(line)
            if line.startswith('<') and line.endswith('>'):
                if not lines:
                   isbold = True
                elif not isbold:
                    lines = []
                    #print('== delete ==')
                    continue
            elif isbold:
                lines = []
                #print('== delete ==')
                isbold = False
            line = line.replace('<strong>', '').replace('</strong>', '') \
                       .replace('<em>', '').replace('</em>', '') \
                       .replace('<b>', '').replace('</b>', '') \
                       .replace('<i>', '').replace('</i>', '') \
                       .replace('<u>', '').replace('</u>', '') \
                       .replace('<o:p>', '').replace('</o:p>', '')
            line = re32.sub('', re31.sub('', re30.sub('', line)))
            #if not lines:
            line0 = re0.sub('', line)
            if '<' in line:
                print('\nWARNING: Invalid token: url {}, line: {}'
                              .format(link, line))
                is_invalid = True
                break
            line = utils.norm_text2(line).strip() if line0 else None
            if line and re23.search(line):
                line0 = line.lower().strip()
                if line0.startswith('глава') or line0.startswith('часть') \
                                             or re20.match(line0) \
                or '©' in line or re21.search(line) or re22.search(line):
                    continue
                lines.append(line)
                #print(line)
                if len(lines) >= MAX_TEXT_LINES:
                    break
        if len(lines) >= MAX_TEXT_LINES or is_invalid:
            break
    res, text = False, None
    while len(lines) >= MIN_TEXT_LINES:
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
            if num_words > MAX_CHUNK_WORDS:
                lines = lines[:-1]
                continue
            if num_words >= MIN_CHUNK_WORDS:
                res = True
        else:
            if not SILENT:
                print('{}: non-Cyrillic'.format(link_no))
            text = None
        break
    if not res:
        if not SILENT:
            if not text:
                if not SILENT:
                    print('no text')
                    #if nop:
                    #    exit()
            else:
                print('text beyond limits:')
                print(text)
        continue
    texts_total += 1
    if time0:
        time1 = time.time()
        eta = (time1 - time0) \
            * (utils.TEXTS_FOR_SOURCE - start_texts_total - texts_total) \
            / texts_total
    if link_no > start_link_idx:
        with open(page_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            f.write(page)
    with open(text_fn, 'wt', encoding='utf-8') as f:
        print(link, file=f)
        f.write(text)
    print('\r', ' ' * 60, end='')
    print('\r{} (of {})'.format(texts_total,
                                min(utils.TEXTS_FOR_SOURCE, num_links)),
          end='')
    if eta:
        print('; ETA: {}'.format(seconds_to_strtime(eta)),
              end='')
    need_enter = True
    #exit()
if need_enter:
    print()
    if time0:
        print('Total time:', seconds_to_strtime(time.time() - time0))

'''===========================================================================
Chunks creation
==========================================================================='''
chunk_fns = utils.get_file_list(utils.CHUNKS_DIR, utils.TEXTS_FOR_SOURCE)
if not chunk_fns:
    text_fns = utils.get_file_list(utils.TEXTS_DIR, utils.TEXTS_FOR_SOURCE)
    text_idx = 0
    for text_idx, text_fn in enumerate(text_fns[:utils.CHUNKS_FOR_SOURCE],
                                       start=1):
        chunk_fn = text_fn.replace(utils.TEXTS_DIR, utils.CHUNKS_DIR)
        assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
        with open(text_fn, 'rt', encoding='utf-8') as f_in, \
             open(chunk_fn, 'wt', encoding='utf-8') as f_out:
            f_in.readline()
            f_out.write(f_in.read())
            print('\r{} (of {})'.format(text_idx, utils.CHUNKS_FOR_SOURCE),
                  end='')
    if text_idx:
        print()
elif len(chunk_fns) < utils.CHUNKS_FOR_SOURCE:
    print('The chunks directory is not empty but not full. '
          'Delete all .txt files from there to recreate chunks')
#    exit()

'''===========================================================================
Tokenization
==========================================================================='''
conll_fns = utils.get_file_list(utils.CONLL_DIR, utils.TEXTS_FOR_SOURCE)
if not conll_fns:
    utils.tokenize(utils.TEXTS_FOR_SOURCE, isdialog=False)
elif len(conll_fns) < utils.CONLL_FOR_SOURCE:
    print('The conll directory is not empty but not full. '
          'Delete all .txt files from there to recreate conll')
    exit()
