#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
from datetime import datetime, timedelta
import os
import random
import re
from selenium.common.exceptions import WebDriverException
import time
import traceback

###
import sys
sys.path.append('../')
#sys.path.append(r'C:\prj-git\facebook-post-scraper')
###
#from scraper import extract
import utils
import _twitter
import _utils

SEED = 42
INIT_URL = 'https://getdaytrends.com/ru/russia/'
#INIT_URL = 'https://br-analytics.ru/mediatrends/getAuthors?hub_id=1&selectItemhub_id=1&date=202011&selectItemdate=202011&sortField=ER'
ROOT_URL = 'https://www.twitter.com/'
#https://twitter.com/search?q=%23%D1%8F%D1%83%D0%B2%D0%B0%D0%B6%D0%B0%D1%8E%D0%B4%D0%B6%D1%83%D0%BC&src=typed_query
TIME_FN = os.path.join(utils.PAGES_DIR, 'time.tmp')
AUTHORS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'authors_ignore.tmp')
SKIP_FIRST_TREND_AUTHORS = 5

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
    links = OrderedDict()
    if os.path.isfile(utils.LINKS_FN + '.tmp'):
        with open(utils.LINKS_FN + '.tmp', 'rt', encoding='utf-8') as f:
            links = OrderedDict(x.split('\t') for x in f.read().split('\n') if x)
    t = None
    if os.path.isfile(TIME_FN):
        with open(TIME_FN, 'rt', encoding='utf-8') as f:
            t = datetime.strptime(f.read() + '.000000',
                                  '%Y-%m-%d %H:%M:%S.%f')
    else:
        t = datetime.strptime('{} 00:00:00.000000'
                                  .format((datetime.today()
                                         - timedelta(days=1)).date()),
                              '%Y-%m-%d %H:%M:%S.%f')
    href_prefix = INIT_URL + 'trend/'
    driver = _utils.selenium_init(silent=True)
    try:
        while len(links) < utils.TEXTS_FOR_DOMAIN:
            with open(TIME_FN, 'wt', encoding='utf-8') as f:
                f.write('{} {}'.format(t.date(), t.time()))
            try:
                driver.get(INIT_URL + '{}/{}/'.format(t.date(),
                                                      str(t.time())[:2]))
                need_enter = True
                links_, no_data = [], True
                for res in driver.find_elements_by_css_selector(
                    'table.trends'
                ):
                    for res in res.find_elements_by_tag_name('a'):
                        no_data = False
                        href, text = res.get_attribute('href'), \
                                     res.get_attribute('text')
                        if href.startswith(href_prefix) \
                       and re.match('#?[ЁА-Яёа-я]+$', text):
                            link = href[len(href_prefix):-1]
                            if link not in links:
                               links_.append('\t'.join((text, link)))
                if no_data:
                    print('\r{}'.format(len(links)), end='')
                    break
                if links_:
                    with open(utils.LINKS_FN + '.tmp', 'at',
                              encoding='utf-8') as f:
                        print('\n'.join(links_), file=f)
                print('\r{} of {}'
                          .format(len(links), utils.TEXTS_FOR_DOMAIN),
                      end='')
                #print(d.date(), d.time(), len(links))
                t -= timedelta(hours=1)
            except WebDriverException:
                print(traceback.format_exc())
                time.sleep(10)
    except KeyboardInterrupt as e:
        raise e
    finally:
        driver.quit()
    links = list(links.values())
    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
if need_enter:
    print()

num_links = len(links)
NUM_AUTHORS = max(utils.TEXTS_FOR_DOMAIN // num_links, 10)

'''===========================================================================
Search for page links
==========================================================================='''
start_link_idx, page_links = _utils.load_page_links()
need_enter = False
if start_link_idx is not None:
    authors_ignore = OrderedDict(page_links)
    page_links = OrderedDict(page_links)
    if os.path.isfile(AUTHORS_IGNORE_FN):
        with open(AUTHORS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            authors_ignore.update({x: 1 for x in f.read().split('\n') if x})
    links = links[start_link_idx:]
    if links:
        driver = _twitter.init(silent=False)
        for link_no, link in enumerate(links, start=start_link_idx):
            print('\rpage links: {}; root links processed: ({} of {})'
                      .format(len(page_links), link_no, num_links),
                  end='')
            #link = '%23%D0%A3%D1%84%D0%B0%D0%A2%D0%B0%D0%BC%D0%B1%D0%BE%D0%B2'
            num_authors_ignore = len(authors_ignore)
            page_links_ = _twitter.get_trend_authors(
                link,
                num_authors=NUM_AUTHORS,
                skip_first=SKIP_FIRST_TREND_AUTHORS,
                authors_ignore=authors_ignore,
                driver=driver,
                silent=True
            )
            page_links.update(page_links_)
            _utils.save_page_links(link_no + 1, list(page_links.items()))
            if len(authors_ignore) > num_authors_ignore:
                with open(AUTHORS_IGNORE_FN, 'at', encoding='utf-8') as f:
                    for author_ignore \
                     in list(authors_ignore)[num_authors_ignore:]:
                        print(author_ignore, file=f)
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
exit()
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
        #link = 'http://twitter.com/lentaruofficial'
        page_fn = utils.get_data_path(utils.PAGES_DIR, num_links, link_no)
        text_fn = utils.get_data_path(utils.TEXTS_DIR, num_links, link_no)
        page = None
        if link_no > start_link_idx:
            if not driver:
                driver = _twitter.init(silent=False)
            text, page = _twitter.get_post_text(
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
