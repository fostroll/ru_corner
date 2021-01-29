#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from corpuscula import Conllu, wikipedia_utils
from junky import seconds_to_strtime
import os
import random
import re
import time
from toxine.wikipedia_utils import TokenizedWikipedia

###
import sys
sys.path.append('../')
###
import utils

SEED = 42
MIN_CHUNK_WORDS = 40
MAX_CHUNK_WORDS = 200

if SEED:
    random.seed(SEED)

'''===========================================================================
Headers collection
==========================================================================='''
ARTICLE_NOS_FN = os.path.join(utils.PAGES_DIR, 'article_nos')
if os.path.isfile(ARTICLE_NOS_FN):
    with open(ARTICLE_NOS_FN, 'rt') as f:
        article_nos = [int(x) for x in f.read().split('\n')]
        num_articles_total, article_nos = article_nos[0], article_nos[1:]

else:
    wikipedia_utils.download_wikipedia(lang='RU', root_dir=None,
                                       overwrite=False)
    for max_article_no, _ in enumerate(wikipedia_utils.Wikipedia().titles()):
        pass
    #max_article_no = 3804415  # articles - templates: 3783701
    num_articles_total = max_article_no + 1
    article_nos = list(range(num_articles_total))
    random.shuffle(article_nos)
    article_nos = article_nos[:int(utils.TEXTS_FOR_SOURCE * 1.1)]  # spare for templates
    with open(ARTICLE_NOS_FN, 'wt') as f:
        print(num_articles_total, file=f)
        f.write('\n'.join(str(x) for x in article_nos))

'''===========================================================================
Texts collection
==========================================================================='''
texts_total, num_articles = 0, len(article_nos)
article_nos = {y: x for x, y in enumerate(article_nos)}
page_fns = utils.get_file_list(utils.PAGES_DIR, utils.TEXTS_FOR_SOURCE)
if page_fns and len(page_fns) < utils.TEXTS_FOR_SOURCE:
    print('The pages directory is not empty but not full. '
          'Delete all .txt files from there to recreate pages')
    exit()

if not page_fns:
    re0 = re.compile(r'\W|\d')
    re1 = re.compile(r'[^ЁА-Яёа-я]')
    re5 = re.compile(r'\W')
    file_nos = []
    time0 = time.time()
    for article_no, article in enumerate(wikipedia_utils.Wikipedia()
                                                        .articles()):
        file_no = article_nos.get(article_no)
        if file_no or file_nos:
            if file_no:
                file_nos.append(file_no)
            id_, title, page = article
            if page:
                lines = page.split('\n')
                text_lines = []
                for line in lines:
                    if line and (line[-1] != '.' or line == 'См. также:'):
                        break
                    text_lines.append(line)
                res = False
                while True:
                    text = utils.norm_text2('\n'.join(text_lines).strip())
                    text0 = re0.sub('', text)
                    text1 = re1.sub('', text0)
                    if text0 and len(text1) / len(text0) >= .9:
                        num_words = len([x for x in text.split()
                                           if re5.sub('', x)])
                        if num_words > MAX_CHUNK_WORDS:
                            text_lines = text_lines[:-1]
                            continue
                        if num_words >= MIN_CHUNK_WORDS:
                            res = True
                    break
                if res:
                    if file_no:
                        file_nos.pop()
                    else:
                        file_no = file_nos.pop(0)
                    page_fn = utils.get_data_path(utils.PAGES_DIR,
                                                  utils.TEXTS_FOR_SOURCE,
                                                  file_no)
                    text_fn = utils.get_data_path(utils.TEXTS_DIR,
                                                  utils.TEXTS_FOR_SOURCE,
                                                  file_no)
                    time1 = time.time()
                    eta = (time1 - time0) \
                        * (num_articles_total - article_no - 1) \
                        / (article_no + 1)
                    article_no = '#{}: '.format(article_no)
                    with open(page_fn, 'wt', encoding='utf-8') as f:
                        print(article_no, end='', file=f)
                        f.write('\n'.join([id_, title + '\n\n', page]))
                    with open(text_fn, 'wt', encoding='utf-8') as f:
                        print(article_no, end='', file=f)
                        f.write('\n'.join([id_, title + '\n', text]))
                    texts_total += 1
                    print('\n{} (of {}); ETA: {}'
                              .format(texts_total,
                                      num_articles,#utils.TEXTS_FOR_SOURCE,
                                      seconds_to_strtime(eta)))
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
    exit()

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
