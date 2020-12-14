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
ROOT_URL = 'https://ria.ru'
URL = ROOT_URL + '/interview/'
SENT_STARTS = ['-', '–', '—', '―']
SPEAKER_A, SPEAKER_B = 'Вопрос', 'Ответ'
MAX_SPEAKER_LEN = 20

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
    re0 = re.compile(r'<a href="([^">]+)" '
                     r'class="list-item__title color-font-hover-only">')
    re1 = re.compile(r'<div class="list-more" data-url="([^">]+)">')
    re2 = re.compile(r'<div class="list-items-loaded" '
                     r'data-next-url="([^">]+)">')
    res = utils.get_url(URL)
    page = res.text
    res = re0.findall(page)
    assert res, 'ERROR: no links found on the main page'
    for link in res:
        links[unescape(link)] = 1
    print('\r{}'.format(len(links)), end='')
    res = re1.search(page)
    assert res, 'ERROR: no next link found on the main page'
    next_link = unescape(res.group(1))
    while True:
        res = utils.get_url(ROOT_URL + next_link)
        page = res.text
        res = re0.findall(page)
        if not res:
            break
        for link in res:
            link = unescape(link)
            if not link.startswith('https://'):
                link = ROOT_URL + link
            links[link] = 1
        print('\r{}'.format(len(links)), end='')
        res = re2.search(page)
        if not res:
            break
        next_link = unescape(res.group(1))
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

re0 = re.compile(r'<(?:p|div[^>]*)>(.+?)</p>')
re1 = re.compile(r'<(/?strong)>')
re2 = re.compile(r'<span[^>]*>.+?</span>')
re2a = re.compile(r'<.*?>|\(.*?\)')
re3 = re.compile(r'{strong}(.+?){/strong}')
need_enter = False
for link_no, link in enumerate(links, start=1):
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    #link = 'https://rsport.ria.ru/20160311/902957688.html'
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
    lines, key_lines = [], 0
    issent = False
    prev_speaker, prev_strong, curr_speaker = None, None, None
    for line in res:
        line = unescape(line).replace('</strong><strong>', '')
        line = re1.sub(r'{\g<1>}', line)
        line = re2.sub('', line)
        line = re2a.sub(' ', line).strip()
        sents = [x.strip() for x in line.split('{strong')
                           for x in x.split('/strong}')]
        for sent in sents:
            if sent.startswith('}') and sent.endswith('{'):
                sent = sent[1:-1].strip()
                speaker, strong = SPEAKER_A, True
            else:
                speaker, strong = SPEAKER_B, False
            if curr_speaker:
                speaker = curr_speaker
            if sent:
                if sent in SENT_STARTS:
                    curr_speaker = None
                    issent = True
                    continue
                if sent[0] in SENT_STARTS:
                    curr_speaker = None
                    sent = sent[1:].lstrip()
                elif not issent:
                    #if prev_speaker and speaker == prev_speaker:
                    if prev_speaker and not (strong or prev_strong):
                        speaker = ''
                    else:
                        continue
                pos_ = 0
                while pos_ == 0:
                    pos_ = sent.find(':')
                    if pos_ == 0:
                        sent = sent[1:]
                if pos_ > 0 and pos_ <= MAX_SPEAKER_LEN:
                    speaker_ = sent[:pos_]
                    sent_ = sent[pos_ + 1:].lstrip()
                    if not sent_:
                        curr_speaker = speaker_
                        issent = True
                        continue
                    if sent_[0].isupper():
                        speaker, sent = speaker_, sent_
                if speaker:
                    key_lines += 1
                sent = speaker + '\t' + ' '.join(sent.split())
                lines.append(sent)
                issent = False
                if speaker:
                    prev_speaker, prev_strong = speaker, strong
                curr_speaker = None
    if key_lines >= _utils.MIN_TEXT_LINES:
        texts_total += 1
        if link_no > start_link_idx:
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
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
_utils.make_chunks(num_links)#, moderator=SPEAKER_A)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(num_links)
