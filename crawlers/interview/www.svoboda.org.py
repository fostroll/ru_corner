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
ROOT_URL = 'https://www.svoboda.org'
URL_1 = '/interviews'
URL_2 = '?p={}'
URL = ROOT_URL + URL_1
SENT_STARTS = ['-', '–', '—', '―']
SPEAKER_A, SPEAKER_B = 'Вопрос', 'Ответ'
MIN_TEXT_LINES = 4
MIN_CHUNK_LINES = 4

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
    re0 = re.compile(r'<a href="([^"]+)" >\n'
                     r'<h4 class="media-block__title '
                     r'media-block__title--size-\d" title=')
    re1 = re.compile(r'<a class="btn link-showMore[^>]+ href="{}\{}(\d+)"'
                          .format(URL_1, URL_2.format('')))
    page_no = '0'
    while page_no:
        res = utils.get_url(URL + (URL_2.format(page_no)
                                       if page_no != '0' else
                                   ''))
        page = res.text
        pos = page.find('href="{}"'.format(URL_1))
        assert pos >= 0, 'ERROR: start block is not found on the page {}' \
                             .format(page_no)
        page = page[pos:]
        pos = page.find('href="/news"')
        assert pos >= 0, 'ERROR: end block is not found on the page {}' \
                         .format(page_no)
        page = page[:pos]
        res = re0.findall(page)
        assert res, \
               'ERROR: no article links found on the page {}'.format(page_no)
        for link in res:
            links[ROOT_URL + link] = 1
        print('\r{}'.format(len(links)), end='')
        res = re1.search(page)
        page_no = res.group(1) if res else None
    links = list(links)

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

re2 = re.compile(r'\n.*<figure(?:.|\n)+?</figure>')
re2a = re.compile(r'\n.*<blockquote(?:.|\n)+?</blockquote>.*\n')
re3 = re.compile(r'\n<a class="wsw__a"(?:.|\n)+?</a>')
re4 = re.compile(r'<a class="wsw__a"[^>]+>(.+?)</a>')
re0 = re.compile(r'<p>((?:.|\n)*?)</p>')
re1 = re.compile(r'<.*?>|\(.*?\)')
need_enter = False
for link_no, link in enumerate(links, start=1):
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    #link = 'https://www.svoboda.org/a/27016704.html'
    #link_no = 1490
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
    pos = res.find('<div id="article-content"')
    if pos > 0:
        pos = res.find('<div class="wsw">', pos)
    assert pos, 'ERROR: no article on page #{}'.format(link_no)
    res = res[pos + 17:]
    pos = res.find('<div class="c-author c-author--hlight"')
    if pos < 0:
        pos = res.find('<a href="/news"')
        if pos < 0:
            pos = res.find('<div id="comments"')
    if pos > 0:
        res = res[:pos]
    res = re2.sub(' ', res)
    res = re2a.sub(' ', res)
    res = re3.sub('\n', res)
    res = re4.sub(r'\g<1>', res)
    res = res.replace('\u200b', '\n')

    res = res.replace('</div>', '</div>\n')
    res = res.split('\n')
    lines = []
    isdiv = False
    for line in res:
        line = line.replace('\u200b', '').replace('\ufeff', '') \
                    .replace('й', 'й').replace('ё', 'ё').strip()
        if '</div' in line:#.startswith('</div'):
            isdiv = False
        if isdiv:
            continue
        if line.startswith('<div'):
            isdiv = True
            continue
        lines.append(line)
    res = '\n'.join(lines)

    res = res.replace('<strong><br />', '<strong>') \
             .replace('<br /></strong>', '</strong>') \
             .replace('<br />', '\n')
    res = re0.sub(lambda x: '\n' + x.group(1).replace('\n', '') + '\n', res)

    #ff = open('1111', 'wt', encoding='utf-8')
    #print(res, file=ff)
    #ff.close()
    res = res.split('\n')
    lines, key_lines = [], 0
    prev_speaker, isdiv = None, False
    isem, isstrong = False, False
    for line in res:
        isem_, isstrong_ = False, False
        line = unescape(line).lstrip()
        if '</div' in line:#.startswith('</div'):
            isdiv = False
            continue
        if isdiv or not line:
            continue
        hasdash = False
        if line[0] in SENT_STARTS:
            line = line[1:].lstrip()
            hasdash = True
        speaker = SPEAKER_A
        if line.startswith('<em>'):
            line = line[4:].lstrip()
            isem_ = True
        elif line.endswith('</em>'):
            isem_ = True
        elif line.startswith('<strong>'):
            line = line[8:].lstrip()
            isstrong_ = True
        elif line.endswith('</strong>'):
            isstrong_ = True
        else:
            speaker = SPEAKER_B
        line = line.replace('</strong>', '').replace('</em>', '').strip()
        #print(line, file=ff)
        if line.startswith('<'):
            if line.startswith('<div'):
                isdiv = True
            continue
        line = re1.sub(' ', line).strip()
        if line == '* * *':
            prev_speaker = None
            continue
        if line and any(x.isalnum() for x in line):
            if line[0] in SENT_STARTS:
                line = line[1:].lstrip()
                hasdash = True
            elif not (prev_speaker or hasdash):
                continue
            if (isem_ or isstrong_) and not (isem or isstrong):
                if not hasdash:
                    continue
                isem, isstrong = isem_, isstrong_
            elif (isem and isstrong_) or (isstrong and isem_):
                continue
            #print('+', file=ff)
            if speaker != prev_speaker:
                prev_speaker = speaker
                key_lines += 1
            else:
                speaker = ''
            if not speaker and line[0].islower():
                lines[-1] += ' ' + line
            else:
                line = speaker + '\t' + ' '.join(line.split())
                lines.append(line)
    if key_lines >= MIN_TEXT_LINES:
        texts_total += 1
        if link_no > start_link_idx:
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
        if lines[-1][0] == '\t':
            lines = lines[:-1]
        with open(text_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
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
_utils.make_chunks(num_links, trim_ending=False, moderator=SPEAKER_A,
                   min_chunk_lines=MIN_CHUNK_LINES)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(num_links)
