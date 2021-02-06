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
ROOT_URL = 'https://www.reddit.com'
URL_1 = 'https://gateway.reddit.com/desktopapi/v1/subreddits/Pikabu' \
    '?rtj=only&redditWebClient=web2x&app=web2x-client-production' \
    '&allow_over18=1&include=prefsSubreddit&after={}&dist=25' \
    '&layout=compact&sort=new'
URL_2 = 'https://gateway.reddit.com/desktopapi/v1/postcomments/{}' \
    '?rtj=only&emotes_as_images=true&allow_over18=true&include=prefsSubreddit' \
    '&subredditName=Pikabu&hasSortParam=true&include_categories=true' \
    '&sort=old&onOtherDiscussions=false'
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
MIN_DEPTH = 3
SKIP_FIRST = 4
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

    def assemble_text(doc, ordered=None):
        res, isli = None, None
        if isinstance(doc, list):
            lines, li_no = [], 1
            for line in doc:
                line = assemble_text(line)
                if line:
                    if isinstance(line, tuple):
                        line = line[0]
                        if line:
                            if ordered:
                                prefix = str(li_no) + '.'
                                li_no += 1
                            else:
                                prefix = '-'
                            line = prefix + ' ' + line
                    if line:
                        lines.append(line)
            res, need_space = '', False
            for line in lines:
                need_space_ = line[-1] != '\n'
                res += ' ' * (need_space and need_space_) + line
                need_space = need_space_
        else:
            e = doc['e']
            if e in ['blockquote', 'code', 'spoilertext']:
                res = ''
            elif e in ['br', 'hr', 'table']:
                res = '\n'
            elif e == 'li':
                res = utils.norm_text2(assemble_text(doc['c'])) + '\n'
                isli = True
            elif e == 'link':
                res = utils.norm_text2(doc['t'])
                link = doc['u']
                if res.find(link) < 0:
                    res += ' (' + link + ')'
            elif e == 'list':
                res = assemble_text(doc['c'], ordered=doc['o'])
            elif e in ['par', 'h']:
                res = utils.norm_text2(assemble_text(doc['c'])) + '\n'
            elif e in ['text', 'raw'] \
            or (len(e) == 2 and e[1] == '/' and e[0] >= 'a' and e[0] <= 'z'):
                res = utils.norm_text2(doc['t'])
            else:
                from pprint import pprint
                with open('1111', 'wt', encoding='utf-8') as f:
                    pprint(doc, stream=f)
                assert 0, 'ERROR: Unknown type "{}"'.format(e)
        if res:
            res = re2.sub(' ', re3.sub('\n', res))
        return (res, isli) if isli is not None else res

    def parse_comments(comments, authors_ignore):
        res, lines, authors = False, [], {}
        prev_comment_id = None
        for comment in comments:
            try:
                if comment['isDeleted']:
                    break
                comment_id, parent_id = comment['id'], comment['parentId']
                assert parent_id == prev_comment_id, \
                    'ERROR: Invalid parent id'
                author, author_id = comment['author'], comment['authorId']
                if authors_ignore and author_id in authors_ignore:
                    break
                authors[author_id] = author
                docs = comment['media']['richtextContent']['document']
                line = assemble_text(docs).strip(), author, author_id
                if not line:
                    break
                lines.append(line)
                prev_comment_id = comment_id
            except Exception as e:
                with open('error.log', 'wt',
                          encoding='utf-8') as f:
                    from pprint import pprint
                    print('COMMENTS', file=f)
                    pprint(comments, stream=f)
                    print('\nCOMMENT', file=f)
                    pprint(comment, stream=f)
                    print('\nERROR', file=f)
                    import traceback
                    traceback.print_exc(file=f)
                raise e
        text, header = None, None
        while True:
            if len(lines) < MIN_DEPTH:
                break
            text_ = '\n'.join(x[0] for x in lines)
            text = '\n'.join(x[1] + ' (' + x[2] + ')\t'
                           + x[0].replace('\n', '\n\t') for x in lines)
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
                header = ROOT_URL + comments[0]['permalink']
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

    skip, post_id_candidates = 0, ['']
    for texts_total, page_fn in enumerate(page_fns, start=1):
        with open(page_fn, 'rt', encoding='utf-8') as f:
            f.readline()
            comments = json.load(f)
        post_id_candidates = [comments[0]['postId']]
        skip = SKIP_FIRST
        if os.path.isfile(page_fn.replace(utils.PAGES_DIR, utils.TEXTS_DIR)):
            continue
        parse_comments(comments, None)

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
        while post_id_candidates:
            post_id, post_id_candidates = \
                post_id_candidates[-1], post_id_candidates[:-1]
            if not post_id:
                if retry:
                    break
                retry = True
            while True:
                url = URL_1.format(post_id)
                if not SILENT:
                    print(url)
                res = utils.get_url(url, headers=HEADERS)
                res = res.json()
                err = res.get('code')
                if not err:
                    #with open('reddit_urls', 'at', encoding='utf=8') as f:
                    #    print(url, file=f)
                    break
                if err:
                    print(url)
                    print(res)
                    time.sleep(1)
            post_ids = res.get('postIds')
            if not post_ids:
                print('WARNING: No posts at url {}'.format(url))
                post_id_candidates = ['']
                skip = 0
                continue
            last_success_url = url
            post_id_candidates, post_ids = post_ids, set(post_ids)
            skip += 1
            if skip < SKIP_FIRST:
                continue
            posts, post_id = [], None
            for post in res.get('posts').values():
                post_id_, num_comments = post['id'], post['numComments']
                if post_id_ in posts_ignore:
                    post_id_candidates = ['']
                    skip = 0
                    break
                #print('', post_id_)
                if post_id_ not in post_ids:
                    continue
                post_id = post_id_
                if num_comments >= 9:
                    comments, num_comments = [], 0
                    while True:
                        url = URL_2.format(post_id)
                        res = utils.get_url(url, headers=HEADERS)
                        res = res.json()
                        err = res.get('code')
                        if not err:
                            break
                        print(url)
                        print('WARNING: Invalid response ', end='')
                        print(res)
                        time.sleep(1)
                    res = res.get('comments')
                    inprogress = False

                    def store_post_id(post_id):
                        posts_ignore.add(post_id)
                        with open(POSTS_IGNORE_FN, 'at',
                                  encoding='utf-8') as f:
                            print(post_id, file=f)
                        if texts_total > utils.TEXTS_FOR_SOURCE:
                            raise OverflowError()

                    for comment in res.values():
                        depth = comment['depth']
                        if depth == 0:
                            inprogress = True
                        if inprogress and depth < num_comments \
                                      and num_comments >= MIN_DEPTH \
                                      and parse_comments(comments,
                                                         authors_ignore):
                            texts_total += 1
                            need_enter = True
                            store_post_id(post_id)
                            inprogress = False
                        if inprogress:
                            comments[depth:] = [comment]
                            num_comments = depth
                    if inprogress and num_comments >= MIN_DEPTH \
                                  and parse_comments(comments,
                                                     authors_ignore):
                        texts_total += 1
                        need_enter = True
                        store_post_id(post_id)
        with open('error.log', 'wt',
                  encoding='utf-8') as f:
            print('NO POSTS. Last success url:', file=f)
            print(last_success_url, file=f)
        assert 0
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
utils.tokenize(MAX_FILES, isdialog=True)
