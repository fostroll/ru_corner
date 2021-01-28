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
import utils  # txt = read_doc(fn)


SEED = 42
ROOT_URL = 'https://theatre-library.ru'
INIT_URL = ROOT_URL + '/works/?page={}'
MIN_TEXT_LINES = 4
MAX_TEXT_LINES = 20
MIN_CHUNK_WORDS = 40
MAX_CHUNK_WORDS = 200
SILENT = True

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
    token = '<li class="pager-last last"><a href="/works/?page='
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
        res = res.split(
            "<div class='dw_ch'><div class='dw_ch_ch'><div class='th_d1'>"
        )[1:]
        if page_no != max_page_no and len(res) != 100:
            print('\nWARNING: Only {} books on {}'.format(len(res), url))
        for book in res:
            token = "<a class='uline' href=\""
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find('"')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book_url = book[:pos]
            book = book[pos:]
            token = "<a class='uline' href='/authors/"
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find("'>")
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            author_url = '/authors/' + book[:pos]
            book = book[pos + 2:]
            pos = book.find('<')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            author_name = utils.norm_text2(book[:pos]).strip()
            book = book[pos:]
            token = '<div class="desc2">'
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find('<')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            genre = book[:pos]
            book = book[pos:]
            #pos = genre.find(',')
            #if pos > 0:
            #    genre = genre[:pos]
            token = "<div class='desc2'>Язык оригинала: "
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find('<')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book_ = book[:pos]
            pos = book_.find(';')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            lang = book_[:pos]
            book_ = book_[pos:]
            token = '; период написания: '
            pos = book_.find(token)
            if pos >= 0:
                book_ = book_[pos + len(token):]
                pos = book_.find(' век')
                if pos < 0:
                    pos = book_.find(',')
                centure = book_[:pos] if pos > 0 else book_
            else:
                centure = '<UNK>'
            token = "<div class='desc2'>Формат файла: "
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find('<')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book_ = book[:pos]
            pos = book_.find(';')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            format = book_[:pos]
            links[book_url] = (lang, genre, centure, format, author_url, author_name)
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
langs, genres, centures, formats = {}, {}, {}, {}
for link in links_:
    book_url, lang, genre, centure, format, author_url, author_name = \
        link.split('\t')
    if lang == 'русский' and centure in ['XXI', 'XX', '<UNK>'] \
                         and genre not in [
        'Аннотация, синопсис',
        'Биография, автобиография',
        'Воспоминания, мемуары',
        'Критика, отзывы, интервью',
        'Публикации, статьи, заметки',
        'Сборник произведений',
        'Теоретическая работа, монография',
        'Учебник, учебное пособие'
    ]:
        links[book_url] = author_url
        #if author_url in links:
        #    links[author_url].append(book_url)
        #else:
        #    links[author_url] = [book_url]
'''
    langs[lang] = langs.get(lang, 0) + 1
    genres[genre] = genres.get(genre, 0) + 1
    centures[centure] = centures.get(centure, 0) + 1
    formats[format] = formats.get(format, 0) + 1
with open('langs', 'wt', encoding='utf-8') as f:
    f.write('\n'.join('\t'.join([x, str(y)]) for x, y in sorted(langs.items())))
with open('genres', 'wt', encoding='utf-8') as f:
    f.write('\n'.join('\t'.join([x, str(y)]) for x, y in sorted(genres.items())))
with open('centures', 'wt', encoding='utf-8') as f:
    f.write('\n'.join('\t'.join([x, str(y)]) for x, y in sorted(centures.items())))
with open('formats', 'wt', encoding='utf-8') as f:
    f.write('\n'.join('\t'.join([x, str(y)]) for x, y in sorted(formats.items())))
'''
num_links = len(links)

'''===========================================================================
Texts download
==========================================================================='''
for link_no, link in enumerate(links):
    pos = link.rfind('/')
    page_fn = os.path.join(utils.PAGES_DIR, link[pos + 1:])
    if not os.path.isfile(page_fn):
        page = utils.get_url(ROOT_URL + link)
        with open(page_fn, 'wb') as f:
            f.write(page.content)
    print('\r{} (of {})'.format(link_no, num_links), end='')
print()
exit()

'''===========================================================================
Chunks creation
==========================================================================='''

chunks_fns = utils.get_file_list(utils.CHUNKS_DIR, utils.TEXTS_FOR_SOURCE)
if chunks_fns and len(chunks_fns) < utils.CHUNKS_FOR_SOURCE:
    print('The chunks directory is not empty but not full. '
          'Delete all .txt files from there to recreate chunks')
    exit()
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

'''===========================================================================
Tokenization
==========================================================================='''
conll_fns = utils.get_file_list(utils.CONLL_DIR, utils.TEXTS_FOR_SOURCE)
if conll_fns and len(conll_fns) < utils.CONLL_FOR_SOURCE:
    print('The conll directory is not empty but not full. '
          'Delete all .txt files from there to recreate conll')
    exit()
utils.tokenize(utils.TEXTS_FOR_SOURCE, isdialog=False)
