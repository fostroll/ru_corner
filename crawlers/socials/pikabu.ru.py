#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import json
import os
import random
import re
import time

###
import sys
sys.path.append('../')
###
import utils
import _utils


SEED = 42
ROOT_URL = 'https://pikabu.ru'
INIT_URL = ROOT_URL + '/new?twitmode=1&of=v2&page={}&_={}'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'TE': 'Trailers'
}
AUTHORS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'authors_ignore')
POSTS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'posts_ignore')
MAX_FILES = 10000
MIN_DEPTH = 4
SKIP_FIRST = 100
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
    re0 = re.compile(r'\W|\d')
    re1 = re.compile(r'[^ЁА-Яёа-я]')
    re2 = re.compile(r'[^\S\n]+')
    re3 = re.compile(r'\n+')
    re4 = re.compile(r'#\b\S+\b')
    re5 = re.compile(r'\W')
    re6 = re.compile(r'[a-z]+://\S+')
    re7 = re.compile(r'<p>((?:.|\n)*?)</p>')
    re8 = re.compile(r'<blockquote(?:.|\n)+?</blockquote>')
    re9 = re.compile(r'<figure(?:.|\n)+?</figure>')
    re10 = re.compile(r'<(?:.|\n)*?>')
    re11 = re.compile(r'#comment_\d+$')

    def parse_comments(comments, header, authors_ignore):
        res, lines, authors = False, [], {}
        for comment, author in comments:
            if authors_ignore and author in authors_ignore:
                break
            authors[author] = author
            line = re7.sub(r'\n\g<1>\n', comment)
            line = line.replace('<br>', '\n').replace('<hr>', '\n')
            line = re10.sub('', re9.sub('', re8.sub('', line)))
            line = re2.sub(' ', re3.sub('\n', utils.norm_text2(line)))
            if not line or line.startswith('Комментарий удален.') \
                        or re11.match(line):
                break
            lines.append((line, author))
        text = None
        while True:
            if len(lines) < MIN_DEPTH:
                break
            text_ = '\n'.join(x[0] for x in lines)
            text = '\n'.join(x[1] + '\t' + x[0].replace('\n', '\n\t') \
                                 for x in lines)
            if not SILENT:
                print(text)
            text_ = re6.sub('', text_)
            text0 = re0.sub('', text_)
            text1 = re1.sub('', text0)
            if text0 and len(text1) / len(text0) >= .9:
                num_words = len([x for x in re4.sub('', text_).split()
                                   if re5.sub('', x)])
                if not SILENT:
                    print('<russian>')
                    print(num_words)
                if num_words < _utils.MIN_CHUNK_WORDS:
                    break
                if num_words > _utils.MAX_CHUNK_WORDS:
                    lines = lines[:-1]
                    continue
                res = True
                break
            elif not SILENT:
                print('<foreign>')
                lines = lines[:-1]
                continue
        if res:
            page_fn = utils.get_data_path(utils.PAGES_DIR, MAX_FILES,
                                          texts_total)
            text_fn = utils.get_data_path(utils.TEXTS_DIR, MAX_FILES,
                                          texts_total)
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(header, file=f)
                json.dump(comments, f, indent=4, ensure_ascii=False)
            with open(text_fn, 'wt', encoding='utf-8') as f:
                print('{} ({})'.format(texts_total, header), file=f)
                f.write(text)
            if authors_ignore is not None:
                need_enter = os.path.isfile(AUTHORS_IGNORE_FN)
                with open(AUTHORS_IGNORE_FN, 'at', encoding='utf-8') as f:
                    if need_enter:
                        print(file=f)
                    f.write('\n'.join('\t'.join(x) for x in authors.items()))
                authors_ignore.update(authors)
            print('\r{} (of {})'.format(texts_total, utils.TEXTS_FOR_SOURCE),
                  end='')
        return res

    for texts_total, page_fn in enumerate(page_fns, start=1):
        if os.path.isfile(page_fn.replace(utils.PAGES_DIR, utils.TEXTS_DIR)):
            continue
        with open(page_fn, 'rt', encoding='utf-8') as f:
            header = f.readline().strip()
            comments = json.load(f)
        parse_comments(comments, header, None)

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
    url, last_success_url = None, None
    retry = False
    try:
        page_no = SKIP_FIRST
        while True:
            page_no += 1
            url = INIT_URL.format(page_no, time.time_ns() // 1000000)
            if not SILENT:
                print(url)
            res = utils.get_url(url, headers=HEADERS)
            res = res.json()
            #with open('000.json', 'wt', encoding='utf-8') as f:
            #    from pprint import pprint
            #    pprint(res, stream=f)
            #exit()
            data = res['data']['stories']
            for post in data:
                post, post_id = post['html'], post['id']
                if post_id in posts_ignore:
                    print('WARNING: Post was already processed. Skipping')
                    continue
                match = re.search(
                    '<span class="story__comments-link-count">(\d+)</span>',
                    post
                )
                if not match:
                    print('WARNING: Number of comments is not found')
                    continue
                last_success_url = url
                num_comments = int(match.group(1))
                if num_comments < 12:
                    continue
                match = re.search(
                    'href="({}/story/\S+?_{})#comments">' \
                        .format(ROOT_URL, post_id),
                    post
                )
                if not match:
                    print('WARNING: Link to comments is not found')
                    continue
                url = match.group(1)
                res = utils.get_url(url, headers=HEADERS)
                res = res.text
                #with open('111.html', 'wt', encoding='utf-8') as f:
                #    print(res, file=f)
                #exit()
                pos = res.find(
                    '<div class="comments__container_main comments__container" data-story-id="{}">'
                        .format(post_id)
                )
                if pos < 0:
                    print('ERROR: Invalid format')
                    with open('error.log', 'wt', encoding='utf-8') as f:
                        print(url, file=f)
                        print(res, file=f)
                    assert 0

                def store_post_id(post_id):
                    posts_ignore.add(post_id)
                    with open(POSTS_IGNORE_FN, 'at',
                              encoding='utf-8') as f:
                        print(post_id, file=f)
                    if texts_total > utils.TEXTS_FOR_SOURCE:
                        raise OverflowError()

                comments, num_comments = [], 0
                inprogress = False
                while True:
                    res = res[pos:]
                    pos = res.find('<div class="comment"')
                    if pos < 0:
                        if inprogress and num_comments >= MIN_DEPTH \
                                      and parse_comments(comments, url,
                                                         authors_ignore):
                            texts_total += 1
                            need_enter = True
                            store_post_id(post_id)
                        break
                    res = res[pos:]
                    token = 'data-indent="'
                    pos = res.find(token)
                    res = res[pos + len(token):]
                    pos = res.find('"')
                    depth = int(res[:pos])
                    if depth == 0:
                        inprogress = True
                    if inprogress and depth < num_comments \
                                  and num_comments >= MIN_DEPTH \
                                  and parse_comments(comments, url,
                                                     authors_ignore):
                        texts_total += 1
                        need_enter = True
                        store_post_id(post_id)
                        inprogress = False
                    if inprogress:
                        token = '<div class="comment__user"'
                        pos = res.find(token)
                        author = res[pos + len(token):]
                        token = 'data-name="'
                        pos = author.find(token)
                        author = author[pos + len(token):]
                        pos = author.find('"')
                        author = author[:pos]
                        token = '<div class="comment__content">'
                        pos = res.find(token)
                        comment = res[pos + len(token):]
                        pos = comment.find('<div class="comment__controls')
                        comment = comment[:pos].rstrip()
                        for token in ['<!--noindex-->', '</div>']:
                            if not comment.endswith(token):
                                print('ERROR: Invalid format')
                                with open('error.log', 'wt',
                                          encoding='utf-8') as f:
                                    print(url, file=f)
                                    print(comment, file=f)
                                    print(file=f)
                                    print(res, file=f)
                                assert 0
                            comment = comment[:-len(token)].strip()
                        comments[depth:] = [(comment, author)]
                        num_comments = depth
        with open('error.log', 'wt',
                  encoding='utf-8') as f:
            print('NO POSTS. Last success url:', file=f)
            print(last_success_url, file=f)
        assert 0
    except OverflowError:
        pass
if need_enter:
    print()

if os.path.isfile(utils.get_data_path(utils.CHUNKS_DIR, MAX_FILES,1)):
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
utils.tokenize(MAX_FILES, isdialog=True)
