#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import os
import random
import re

###
import sys
sys.path.append('../')
#sys.path.append(r'C:\prj-git\facebook-post-scraper')
###
#from scraper import extract
import utils
import _facebook
import _utils

SEED = 42
INIT_URL = 'https://citifox.ru/2019/11/07/top-1000-interesnykh-person-russkogo-feys/'
ROOT_URL = 'https://www.facebook.com/'

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
    res = utils.get_url(INIT_URL).text
    pos = res.find('<ol>')
    if pos > 0:
        res = res[pos + 4:]
    pos = res.find('</ol>')
    if pos > 0:
        res = res[:pos]
    for link in re.findall(r'<li>[^<]*<a href="([^">]+)">', res):
        # workaround
        if not link.startswith(ROOT_URL):
            pos = link.find(ROOT_URL.replace('//', '/'))
            assert pos >= 0, 'ERROR: Incorrect url ' + link
            if pos > 0:
                link = link[pos:].replace('/', '//', 1)
        ###
        links.append(link)
    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))

num_links = len(links)
NUM_AUTHORS = utils.TEXTS_FOR_DOMAIN // num_links

'''===========================================================================
Search for page links
==========================================================================='''
start_link_idx, page_links = _utils.load_page_links()
need_enter = False
if start_link_idx is not None:
    page_links = OrderedDict(page_links)
    links = links[start_link_idx:]
    if links:
        driver = _facebook.init(silent=False)
        for link_no, link in enumerate(links, start=start_link_idx):
            print('\rpage links: {}; root links processed: ({} of {})'
                      .format(len(page_links), link_no, num_links),
                  end='')
            #link = 'https://www.facebook.com/profile.php?id=100003259844721'
            #link = 'https://www.facebook.com/elftorgovec'
            page_links_ = _facebook.get_comment_authors(
                link,
                num_authors=_utils.NUM_AUTHORS,
                depth=_utils.SEARCH_DEPTH,
                post_limit=_utils.POST_LIMIT,
                authors_ignore=list(page_links) + links,
                driver=driver,
                silent=True
            )
            page_links.update(page_links_)
            _utils.save_page_links(link_no + 1, list(page_links.items()))
            need_enter = True
            #exit()
        print('\rpage links: {}; root links processed: {} (of {})'
                  .format(len(page_links), link_no + 1, num_links),
              end='')
        driver.quit()
    page_links = list(page_links.items())
    random.shuffle(page_links)
    _utils.save_page_links(None, page_links)
if need_enter:
    print()

num_page_links = len(page_links)

'''===========================================================================
Texts download and parse
==========================================================================='''
page_fns = utils.get_file_list(utils.PAGES_DIR, num_page_links)
start_link_idx = int(os.path.split(sorted(page_fns)[-1])[-1]
                         .replace(utils.DATA_EXT, '')) \
                     if len(page_fns) > 0 else \
                 0
texts_total = 0

if texts_total < utils.TEXTS_FOR_SOURCE:
    need_enter = False
    driver = None
    for link_no, (link, _) in enumerate(page_links, start=1):
        if texts_total >= utils.TEXTS_FOR_SOURCE:
            break
        #link = 'https://www.facebook.com/profile.php?id=100003259844721'
        page_fn = utils.get_data_path(utils.PAGES_DIR, num_links, link_no)
        text_fn = utils.get_data_path(utils.TEXTS_DIR, num_links, link_no)
        page = None
        if link_no > start_link_idx:
            if not driver:
                driver = _facebook.init(silent=False)
            text, page = _facebook.get_post_text(
                link,
                min_words=_utils.MIN_CHUNK_WORDS,
                max_words=_utils.MAX_CHUNK_WORDS,
                post_limit=_utils.POST_LIMIT,
                driver=driver,
                silent=True
            )
        else:
            if not os.path.isfile(page_fn):
                continue
            if os.path.isfile(text_fn):
                texts_total += 1
                continue
            with open(page_fn, 'rt', encoding='utf-8') as f:
                link = f.readline().rstrip()
                page = f.read()
        if text:
            texts_total += 1
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
            with open(text_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(text)
            print('\r{} (of {})'.format(texts_total,
                                        min(utils.TEXTS_FOR_SOURCE,
                                            num_page_links)),
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
_utils.make_chunks(num_page_links)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(num_page_links, isdialog=False)
