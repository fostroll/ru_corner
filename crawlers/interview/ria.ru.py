#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from html import unescape
import json
import os
import random
import re

###
import sys
sys.path.append('../')
###
import utils


SEED = 42
ROOT_URL = 'https://ria.ru'
URL = ROOT_URL + '/interview/'
SENT_STARTS = ['-', '–', '—', '―']
SPEAKER_A, SPEAKER_B = 'Вопрос', 'Ответ'

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Downloading of the list of links
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt') as f:
        links = [x for x in f.read().split('\n') if x]

else:
    re0 = re.compile('<a href="([^">]+)" class="list-item__title color-font-hover-only">')
    re1 = re.compile('<div class="list-more" data-url="([^">]+)">')
    re2 = re.compile('<div class="list-items-loaded" data-next-url="([^">]+)">')
    res = utils.get_url(URL)
    html = res.text
    res = re0.findall(html)
    assert res, 'ERROR: no links found on the main page'
    for link in res:
        links.append(unescape(link))
    print('\r{}'.format(len(links)), end='')
    res = re1.search(html)
    assert res, 'ERROR: no next link found on the main page'
    next_link = unescape(res.group(1))
    while True:
        res = utils.get_url(ROOT_URL + next_link)
        html = res.text
        res = re0.findall(html)
        if not res:
            break
        for link in res:
            link = unescape(link)
            if not link.startswith('https://'):
                print('\n{} : no root!'.format(link))
                link = ROOT_URL + link
            links.append(link)
        print('\r{}'.format(len(links)), end='')
        res = re2.search(html)
        if not res:
            break
        next_link = unescape(res.group(1))

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt') as f:
        f.write('\n'.join(links))
    print()

'''===========================================================================
Downloading and parse texts
==========================================================================='''
text_fns = utils.get_file_list(utils.TEXTS_DIR, len(links))
total_texts = len(text_fns)
if total_texts < utils.TEXTS_FOR_SOURCE:
    start_link_idx = int(os.path.split(sorted(text_fns)[-1])[-1]
                             .replace(utils.DATA_EXT, '')) \
                         if total_texts > 0 else \
                     0

    re0 = re.compile('<p>(.+?)</p>')
    re1 = re.compile('<(/?strong)>')
    re2 = re.compile('<.*?>|\(.*?\)')
    re3 = re.compile('{strong}(.+?){/strong}')
    for link_no, link in enumerate(links[start_link_idx:],
                                   start=start_link_idx + 1):
        #link = 'https://ria.ru/20081210/156918393.html'
        res = utils.get_url(link)
        res = res.text
        res = re0.findall(res)
        lines, key_lines = [], 0
        issent = False
        prev_speaker = None
        for line in res:
            line = unescape(line).replace('</strong><strong>', '')
            line = re1.sub(r'{\g<1>}', line)
            line = re2.sub(' ', line).strip()
            sents = [x.strip() for x in line.split('{strong')
                               for x in x.split('/strong}')]
            for sent in sents:
                if sent.startswith('}') and sent.endswith('{'):
                    sent = sent[1:-1].strip()
                    speaker = SPEAKER_A
                else:
                    speaker = SPEAKER_B
                if sent:
                    if sent in SENT_STARTS:
                        issent = True
                        continue
                    if sent[0] in SENT_STARTS:
                        sent = sent[1:].lstrip()
                    elif not issent:
                        if prev_speaker and speaker == prev_speaker:
                            speaker = ''
                        else:
                            continue
                    if speaker:
                        key_lines += 1
                    sent = speaker + '\t' + ' '.join(sent.split())
                    lines.append(sent)
                    issent = False
                    if speaker:
                        prev_speaker = speaker
        if key_lines >= utils.MIN_TEXT_LINES:
            total_texts += 1
            with open(utils.get_data_path(utils.TEXTS_DIR,
                                          len(links), link_no),
                      'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write('\n'.join(lines))
            print('\r{} (of {})'.format(total_texts,
                                        utils.TEXTS_FOR_SOURCE),
                  end='')
        #exit()
        if total_texts >= utils.TEXTS_FOR_SOURCE:
            break
    print()

'''===========================================================================
Chunks creation
==========================================================================='''
utils.make_chunks(len(links), moderator=SPEAKER_A)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(len(links))
