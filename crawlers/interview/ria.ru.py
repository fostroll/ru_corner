#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
from corpuscula import Conllu
from html import unescape
import json
import os
import random
import re
import requests
from textdistance import damerau_levenshtein
from toxine.text_preprocessor import TextPreprocessor
distance = damerau_levenshtein.distance

###
import sys
sys.path.append('../')
###
import utils


SEED = None  #42
ROOT_URL = 'https://ria.ru'
URL = ROOT_URL + '/interview/'
SENT_STARTS = ['-', '–', '—', '―']

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
    res = requests.get(URL, allow_redirects=True)
    html = res.text
    res = re0.findall(html)
    assert res, 'ERROR: no links found on the main page'
    for link in res:
        links.append(ROOT_URL + unescape(link))
    print('\r{}'.format(len(links)), end='')
    res = re1.search(html)
    assert res, 'ERROR: no next link found on the main page'
    next_link = ROOT_URL + unescape(res.group(1))
    while True:
        res = requests.get(next_link, allow_redirects=True)
        html = res.text
        res = re0.findall(html)
        if not res:
            break
        for link in res:
            links.append(ROOT_URL + unescape(link))
        print('\r{}'.format(len(links)), end='')
        res = re2.search(html)
        if not res:
            break
        next_link = ROOT_URL + unescape(res.group(1))

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt') as f:
        f.write('\n'.join(links))

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
    re2 = re.compile('<.*?>')
    re3 = re.compile('{strong}(.+?){/strong}')
    for link_no, link in enumerate(links[start_link_idx:],
                                   start=start_link_idx + 1):
        res = requests.get(link, allow_redirects=True)
        res = res.text
        res = re0.findall(res)
        lines = []
        isstarted = False
        for line in res:
            line = unescape(line).replace('</strong><strong>', '')
            line = re1.sub(r'{\g<1>}', line)
            line = re2.sub(' ', line).strip()
            sents = [x.strip() for x in line.split('{strong')
                               for x in x.split('/strong}')]
            issent = False
            for sent in sents:
                if sent.startswith('}') and sent.endswith('{'):
                    sent = sent[1:-1].strip()
                    speaker = '1'
                else:
                    speaker = '2'
                if sent:
                    if sent in SENT_STARTS:
                        issent = True
                        continue
                    if sent[0] in SENT_STARTS:
                        sent = sent[1:].lstrip()
                    elif not issent:
                        if isstarted and speaker == '2':
                            speaker = ''
                        else:
                            continue
                    sent = speaker + '\t' + ' '.join(sent.split())
                    lines.append(sent)
                    issent = False
                    if speaker == '1':
                        isstarted = True
        if lines:
            total_texts += 1
            with open(utils.get_data_path(utils.TEXTS_DIR,
                                          len(links), link_no),
                      'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write('\n'.join(lines))
            print('\r{} (of {})'.format(total_texts,
                                        utils.TEXTS_FOR_SOURCE),
                  end='')
        if total_texts >= utils.TEXTS_FOR_SOURCE:
            break
    print()
exit()
'''===========================================================================
Chunks creation
==========================================================================='''
text_fns = utils.get_file_list(utils.TEXTS_DIR, len(links))
texts_processed = 0
for text_idx, text_fn in enumerate(text_fns[:utils.CHUNKS_FOR_SOURCE],
                                   start=1):
    chunk_fn = text_fn.replace(utils.TEXTS_DIR, utils.CHUNKS_DIR)
    assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
    if not os.path.isfile(chunk_fn):
        with open(text_fn, 'rt', encoding='utf-8') as f_in:
            text = [x.split('\t') for x in f_in.read().split('\n') if x][1:]
        with open(chunk_fn, 'wt', encoding='utf-8') as f_out:
            moder_ = None
            for start_idx, (speaker, _) in enumerate(text):
                if speaker:
                    moder_ = speaker
                    break
            assert moder_, 'ERROR: invalid file content'
            speaker_lines, speaker_words = {}, {}
            curr_speaker = None
            for speaker, line in text:
                if speaker:
                    curr_speaker = speaker
                    speaker_lines[speaker] = \
                        speaker_lines.get(speaker, 0) + 1
                if curr_speaker:
                    speaker_words[curr_speaker] = \
                        speaker_words.get(curr_speaker, 0) + len(line.split())
            max_lines = max(speaker_lines.values())
            moder = min({x: y / speaker_lines[x]
                             for x, y in speaker_words.items()
                             if speaker_lines[x] > max_lines / 2}.items(),
                        key=lambda x: x[1])[0]
            eff_start_idx = len(text) * 2 // 3
            for i, (speaker, _) in \
                    enumerate(reversed(text[:eff_start_idx + 1])):
                if speaker == moder:
                    eff_start_idx -= i
                    break
            else:
                for i, (speaker, _) in enumerate(text[eff_start_idx:]):
                    if speaker == moder:
                        eff_start_idx += i
                        break
                else:
                    eff_start_idx = start_idx

            end_idx, next_id = 0, 0
            for idx, (speaker, _) in reversed(list(enumerate(text))):
                if speaker:
                    if not end_idx:
                        end_idx = idx + 1
                    if speaker == moder:
                        end_idx = idx
                        break
                    if next_id > 2:
                        break
                    next_id += 1

            text = text[start_idx:end_idx]
            lines = []
            speaker_no, chunk_words = 0, 0
            for speaker, line in text[eff_start_idx:]:
                lines.append('\t'.join([speaker, line]))
                chunk_words += len(line.split())
                if speaker:
                    speaker_no += 1
                if speaker_no >= utils.MIN_CHUNK_LINES \
               and chunk_words >= utils.MIN_CHUNK_WORDS:
                    break
            else:
                for speaker, line in reversed(text[:eff_start_idx]):
                    lines.insert(0, '\t'.join([speaker, line]))
                    chunk_words += len(line.split())
                    if speaker:
                        speaker_no += 1
                    if speaker_no >= utils.MIN_CHUNK_LINES \
                   and chunk_words >= utils.MIN_CHUNK_WORDS:
                        break
            f_out.write('\n'.join(lines))
            print('\r{} (of {})'.format(text_idx, utils.CHUNKS_FOR_SOURCE),
                  end='')
            texts_processed += 1
if texts_processed:
    print()

'''===========================================================================
Tokenization
==========================================================================='''
tp = TextPreprocessor()
chunk_fns = utils.get_file_list(utils.CHUNKS_DIR, len(links))
texts_processed = 0
for chunk_idx, chunk_fn in enumerate(chunk_fns[:utils.CONLL_FOR_SOURCE],
                                     start=1):
    conll_fn = chunk_fn.replace(utils.CHUNKS_DIR, utils.CONLL_DIR)
    assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
    if not os.path.isfile(conll_fn):
        doc_id = utils.fn_to_id(conll_fn)
        with open(chunk_fn, 'rt', encoding='utf-8') as f_in:
            text = [x.split('\t') for x in f_in.read().split('\n') if x]
        tp.new_doc(doc_id=doc_id, metadata=[])
        curr_speaker = None
        speakers, pars = [], []
        for speaker, sentence in text:
            if speaker:
                if speaker != curr_speaker:
                    curr_speaker = speaker
            else:
                speaker = curr_speaker
            speakers.append(curr_speaker)
            pars.append(sentence)
        speaker_list = {x: str(i) for i, x in
                            enumerate(OrderedDict(zip(speakers, speakers)),
                                      start=1)}

        tp.new_pars(pars, doc_id=doc_id)
        tp.do_all(silent=True)
        conll = list(tp.save(doc_id=doc_id))
        tp.remove_doc(doc_id)

        speakers = iter(speakers)
        for sentence in conll:
            sent, meta = sentence
            if 'newpar id' in meta:
                meta['speaker'] = speaker_list[next(speakers)]
        Conllu.save(conll, conll_fn, log_file=None)
        print('\r{} (of {})'.format(chunk_idx, utils.CONLL_FOR_SOURCE),
              end='')
        texts_processed += 1
if texts_processed:
    print()
