#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import os
import random
import re

###
import sys
sys.path.append('../')
###
import utils
import _instagram
import _utils

SEED = 42
INIT_URL = 'https://starngage.com/app/global/influencer/ranking/russian-federation?page={}'
ROOT_URL = 'https://www.instagram.com/'
LIKERS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'likers_ignore.tmp')

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Links download
==========================================================================='''
need_enter = False
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]

else:
    for page_no in range(1, 11):
        res = utils.get_url(INIT_URL.format(page_no)).text
        pos = res.find('<tbody>')
        if pos > 0:
            res = res[pos + 7:]
        pos = res.find('</tbody>')
        if pos > 0:
            res = res[:pos]
        for link in re.findall(r'href="https://starngage.com/app/global/influencers/([^">]+)"', res):
            links.append(ROOT_URL + link)
        print('\r{} of 10: {} links found'.format(page_no, len(links)),
              end='')
    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
if need_enter:
    print()

num_links = len(links)
NUM_LIKERS = max(utils.TEXTS_FOR_DOMAIN * 10 // num_links, 100)
SKIP_LIKERS = (20, 1/3)

'''===========================================================================
Search for page links
==========================================================================='''
start_link_idx, page_links = _utils.load_page_links()
need_enter = False
if start_link_idx is not None:
    likers_ignore = OrderedDict(page_links)
    page_links = OrderedDict(page_links)
    if os.path.isfile(LIKERS_IGNORE_FN):
        with open(LIKERS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            likers_ignore.update({x: 1 for x in f.read().split('\n') if x})
    links = links[start_link_idx:]
    if links:
        driver = _instagram.init(silent=False)
        for link_no, link in enumerate(links, start=start_link_idx):
            print('\rpage links: {}; root links processed: ({} of {})'
                      .format(len(page_links), link_no, num_links),
                  end='')
            #link = 'https://www.instagram.com/korablik.shop'
            num_likers_ignore = len(likers_ignore)
            page_links_ = _instagram.get_likers(
                link,
                num_likers=NUM_LIKERS,
                skip=SKIP_LIKERS,
                post_limit=_utils.POST_LIMIT,
                likers_ignore=likers_ignore,
                driver=driver,
                silent=True
            )
            page_links.update(page_links_)
            _utils.save_page_links(link_no + 1, list(page_links.items()))
            if len(likers_ignore) > num_likers_ignore:
                with open(LIKERS_IGNORE_FN, 'at', encoding='utf-8') as f:
                    for liker_ignore \
                     in list(likers_ignore)[num_likers_ignore:]:
                        print(liker_ignore, file=f)
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
        #link = 'https://www.instagram.com/stkim91/'
        #link = 'https://www.instagram.com/oleggabidullin/'
        page_fn = utils.get_data_path(utils.PAGES_DIR,
                                      num_page_links, link_no)
        text_fn = utils.get_data_path(utils.TEXTS_DIR,
                                      num_page_links, link_no)
        text, page = None, None
        if link_no > start_link_idx:
            if not driver:
                driver = _instagram.init(silent=False)
                #driver = _utils.selenium_init(silent=False)
            text, page, p_link = _instagram.get_post_text(
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
                print('{} ({})'.format(link, p_link), file=f)
                f.write(page)
            with open(text_fn, 'wt', encoding='utf-8') as f:
                print('{} ({})'.format(link, p_link), file=f)
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
exit()
'''===========================================================================
Chunks creation
==========================================================================='''
_utils.make_chunks(num_page_links)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(num_page_links, isdialog=False)
