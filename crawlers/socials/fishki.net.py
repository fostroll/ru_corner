#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import io
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
ROOT_URL = 'https://fishki.net'
#ROOT_URL = 'https://trinixy.ru'
INIT_URL = ROOT_URL + '/all/'
URL = ROOT_URL + '/{}/'
AUTHORS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'authors_ignore')
POSTS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'posts_ignore')
MAX_FILES = 10000
SILENT = False

if SEED:
    random.seed(SEED)

'''===========================================================================
Texts download and parse
==========================================================================='''
page_fns = utils.get_file_list(utils.PAGES_DIR, MAX_FILES)

need_enter = False
if len(page_fns) < utils.TEXTS_FOR_SOURCE:
    texts_total = 0
    nosp = '(?:.|\n)'
    re0 = re.compile(r'\W|\d')
    re1 = re.compile(r'[^ЁА-Яёа-я]')
    re2 = re.compile(r'[^\S\n]+')
    re3 = re.compile(r'\n+')
    re4 = re.compile(r'#\b\S+\b')
    re5 = re.compile(r'\W')
    re6 = re.compile(r'<{0}*?>'.format(nosp))
    re10 = re.compile(r"data-post-id='(\d+?)'{0}+?"
                      r'<h2 class="content__title h2-small">{0}+?'
                      r'<a href="(.+?)"{0}+?'
                      r'<span itemprop="name">(.+?)</span>{0}+?'.format(nosp))
    re11 = re.compile(r'<p class="expanded-anounce" itemprop="description"'
                      r'>({0}+?)<!--</p>-->'.format(nosp))
    re12 = re.compile(r'<a class="author__link" href="/profile/(\d+?)"'
                      r'>(.+?)</a>{0}+?'.format(nosp))
    def parse_post(post):
        res = False
        match = re10.search(post)
        if not match:
            if not SILENT:
                print("WARNING: Post is not a post. Skipping")
        else:
            post_id, href, title = match.groups()
            if post_id in posts_ignore:
                if not SILENT:
                    print('WARNING: Post was already processed. Skipping')
            else:
                match = re11.search(post)
                if not match:
                    if not SILENT:
                        print("WARNING: Post doesn't have any text. Skipping")
                else:
                    text = match.group(1)
                    match = re12.search(post)
                    if not match:
                        if not SILENT:
                            print('WARNING: Author is unknown. Skipping')
                    else:
                        author_id, author = match.groups()
                        if author_id in posts_ignore:
                            if not SILENT:
                                print('WARNING: Author is already known. '
                                      'Skipping')
                        else:
                            def norm_(text):
                                text = re6.sub('',
                                               text.replace('\n', ' ')
                                                   .replace('<br>', '\n')
                                                   .replace('<br/>', '\n')
                                                   .replace('<br />', '\n'))
                                return '\n'.join(
                                    x for x in (
                                        ' '.join(x.split()).strip()
                                            for x in utils.norm_text2(text)
                                                          .split('\n')
                                    ) if x
                                )
                            title, text = norm_(title), norm_(text)
                            if title and text:
                                res = True
        if res:
            res = None
            if not SILENT:
                print(title)
                print(text)
            text0 = re0.sub('', text)
            text1 = re1.sub('', text0)
            if text0 and len(text1) / len(text0) >= .9:
                num_words = len([x for x in re4.sub('', text).split()
                                   if re5.sub('', x)])
                if not SILENT:
                    print('<russian>')
                    print(num_words)
                if num_words >= _utils.MIN_CHUNK_WORDS \
               and num_words <= _utils.MAX_CHUNK_WORDS:
                    res = post_id, author_id, author
                    text = title + '\n' + text
            elif not SILENT:
                print('<foreign>')
            if res:
                page_fn = utils.get_data_path(utils.PAGES_DIR, MAX_FILES,
                                              texts_total)
                text_fn = utils.get_data_path(utils.TEXTS_DIR, MAX_FILES,
                                              texts_total)
                with open(page_fn, 'wt', encoding='utf-8') as f:
                    f.write(post)
                with open(text_fn, 'wt', encoding='utf-8') as f:
                    print('{} ({})'.format(texts_total, ROOT_URL + href),
                          file=f)
                    f.write(text)
                print('\r{} (of {})' \
                          .format(texts_total, utils.TEXTS_FOR_SOURCE),
                      end='')
        return res

    for texts_total, page_fn in enumerate(page_fns, start=1):
        if os.path.isfile(page_fn.replace(utils.PAGES_DIR, utils.TEXTS_DIR)):
            continue
        with open(page_fn, 'rt', encoding='utf-8') as f:
            post = f.read()
        parse_post(post)

    texts_total += 1
    if os.path.isfile(AUTHORS_IGNORE_FN):
        with open(AUTHORS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            authors_ignore = OrderedDict(x.split('\t')
                                             for x in f.read().split('\n')
                                             if x)
    else:
        authors_ignore = OrderedDict()
    if os.path.isfile(POSTS_IGNORE_FN):
        with open(POSTS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            posts_ignore = set(x for x in f.read().split('\n') if x)
    else:
        posts_ignore = set()
    res = utils.get_url(INIT_URL)
    res = res.text
    pos = res.find('id="main-content"')
    assert pos > 0, 'ERROR: Invalid root page'
    res = res[pos:]
    pos = res.find('<div')
    assert pos > 0, 'ERROR: Invalid root page'
    res = res[:pos]
    token = '<a href="/'
    pos = res.rfind(token)
    assert pos > 0, 'ERROR: Invalid root page'
    res = res[pos + len(token):]
    pos = res.find('/"')
    assert pos > 0, 'ERROR: Invalid root page'
    res = res[:pos]
    max_page_no = int(res)
    if not SILENT:
        print('max_page_no =', max_page_no)
    try:
        while True:
            MIN_P, MAX_P = 1e10, -1
            page_nos = list(range(1, max_page_no + 1))
            random.shuffle(page_nos)
            for page_no in page_nos:
                url = URL.format(page_no)
                if not SILENT:
                    print(url)
                res = utils.get_url(url)
                res = res.text
                token = "<div class='drag_element'>"
                pos = res.find(token)
                assert pos > 0, 'ERROR: Invalid root page'
                res = res[pos + len(token):]
                pos = res.find("<div class='clearfix'>")
                assert pos > 0, 'ERROR: Invalid root page'
                res = res[:pos]
                #with open('111.html', 'wt', encoding='utf-8') as f:
                #    print(res, file=f)
                #exit()
                posts = []
                for post in res.split("<div class='drag_element'>"):
                    line = io.StringIO(post.lstrip()).readline()
                    if line.find('is_adv_post') < 0 \
                   and line.find('yandex-adaptive') < 0:
                        posts.append(post)
#<div id="gallery_object_2692943" data-post-id='1747876' data-gallery-id='2692943' class="paddingtop15 gallery expanded-post"  itemscope itemtype="http://schema.org/BlogPosting">
#<div id="gallery_object_2692748" data-post-id='1747849' data-gallery-id='2692748' class="paddingtop15 gallery expanded-post gallery-image"  itemscope itemtype="http://schema.org/BlogPosting">
#<div  data-post-id='46104' data-gallery-id='0' class="paddingtop15 gallery expanded-post"  itemscope itemtype="http://schema.org/BlogPosting">
#<div  data-post-id='1744581' data-gallery-id='0' class="paddingtop15 gallery expanded-post is_adv_post gallery-image"  itemscope itemtype="http://schema.org/BlogPosting">
#<div  data-post-id='1744248' data-gallery-id='0' class="paddingtop15 gallery expanded-post is_adv_post"  itemscope itemtype="http://schema.org/BlogPosting">
#<div id="yandex_rtb_R-A-561366-1" class="yandex-adaptive"></div>
                num_posts = len(posts)
                if num_posts == 0:
                    with open('error.log', 'wt', encoding='utf-8') as f:
                        print(url, file=f)
                        print(res, file=f)
                    print('ERROR: No posts found', num_posts)
                    exit()
                if num_posts < MIN_P:
                    MIN_P = num_posts
                if num_posts > MAX_P:
                    MAX_P = num_posts
                if not SILENT:
                    print('num_posts: {} <= {} <= {}'
                              .format(MIN_P, num_posts, MAX_P))
                post_nos = list(range(num_posts))
                random.shuffle(post_nos)
                for post_no in post_nos:
                    post = posts[post_no]
                    res = parse_post(post)
                    if res:
                        post_id, author_id, author = res
                        posts_ignore.add(post_id)
                        with open(POSTS_IGNORE_FN, 'at',
                                  encoding='utf-8') as f:
                            print(post_id, file=f)
                        author=author.strip()
                        with open(AUTHORS_IGNORE_FN, 'at',
                                  encoding='utf-8') as f:
                            print('{}\t{}'.format(author_id, author), file=f)
                        authors_ignore[author_id] = author
                        texts_total += 1
                        need_enter = True
                        break
                if texts_total > utils.TEXTS_FOR_SOURCE:
                    raise OverflowError()
    except OverflowError:
        pass
if need_enter:
    print()

if os.path.isfile(utils.get_data_path(utils.CHUNKS_DIR, MAX_FILES, 1)):
    print('WARNING: Chunks are already exist. '
          'Delete them if you want to recreate')
    exit()

page_fns = utils.get_file_list(utils.PAGES_DIR, MAX_FILES)
text_fns = utils.get_file_list(utils.TEXTS_DIR, MAX_FILES)
assert len(page_fns) == len(text_fns)
#new_order = utils.shuffle_file_list(page_fns)
utils.shuffle_file_list(text_fns, new_order=None)

'''===========================================================================
Chunks creation
==========================================================================='''
_utils.make_chunks(MAX_FILES)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(MAX_FILES, isdialog=False)
