#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import datetime
from html import unescape
import os
import random
import re

###
import sys
sys.path.append('../')
###
import utils


SEED = 42
ROOT_URL = 'https://www.rulit.me'
INIT_URL = ROOT_URL + '/tag/samizdat/all/{}/date'

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Authors download
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]

else:
    links = OrderedDict()
    res = utils.get_url(INIT_URL.format(1))
    res = res.text
    pos = res.find('/date title="Последняя страница">')
    assert pos >= 0, "ERROR: Can't find authors on {}".format(url)
    res = res[:pos]
    pos = res.rfind('/')
    assert pos >= 0, "ERROR: Can't find authors on {}".format(url)
    max_page_no = int(res[pos + 1:])
    for page_no in range(1, max_page_no + 1):
        url = INIT_URL.format(page_no)
        res = utils.get_url(url)
        res = res.text
        res = res.split('<article class="single-blog post-list">')[1:]
        assert page_no == max_page_no or len(res) == 10, \
            'ERROR: Only {} books on {}'.format(len(res), url)
        for book in res:
            token = '<a href="'
            pos = res.find(token)
            book_url = res[pos + token:]
            pos = book_url.find('"')
            book_url = book_url[:pos]
                            <div class="media">
                                <div class="media-left">
                                    <div>
                                        <a href="https://www.rulit.me/tag/samizdat/sledovatel-i-demon-si-download-625617.html"><img alt="Следователь и Демон [СИ]" src="https://www.rulit.me/data/programs/images/sledovatel-i-demon-si_625617.jpg" width="150" style="margin-top: 15px; margin-left: 15px;"/></a>
                                    </div>
                                </div>
                                <div class="media-body">
                                    <div class="post-content">
                                        <div class="entry-header text-left text-uppercase">
                                            <a href="https://www.rulit.me/tag/samizdat" class="post-cat">Самиздат</a>, <a href="https://www.rulit.me/tag/fantasy" class="post-cat">Фэнтези</a>                                            <h4><a href="https://www.rulit.me/tag/samizdat/sledovatel-i-demon-si-download-625617.html"><strong>Следователь и Демон [СИ]</strong></a></h4>
                                        </div>
                                        <div class="entry-content">
                                            <p>
                                            <div class="book_info">Автор: <a href="https://www.rulit.me/author/aleksandrov-aleksandr-n">Александров Александр Н. <span class=ls_nick></span></a></div>                                            <div class="book_info">Серия: <a href="https://www.rulit.me/series/figaro-sledovatel-departamenta-drugih-del">Фигаро, следователь Департамента Других Дел</a> #2</div>                                                                                        <div class="book_info">Язык: <span class="date_value">русский</span></div>

    res = re.sub(r'<!--(:?.|\n)+?-->\n*', '', res) \
            .replace('Привет всем твоим!', '')
    re0 = re.compile(
        r'<li><tt><small>(?:<A HREF=.+?>)?<b>(dir|www|огл)</b>'
        r'.+?</small></tt> <A HREF=(.+?)><b>(.+?)</b></A>$'
    )
    for line in (x for x in res.split('\n') if x):
        line = unescape(line.rstrip())
        match = re0.match(line)
        if match:
            type_, link, author = match.groups()
            if not link.startswith('http:'):
                link = (ROOT_URL if link.startswith('/') else url) + link
            if link not in links:
                links[link] = (author, type_)
        elif line == '<br>':
            pass
        elif line.startswith('</pre>') \
        or line.startswith('<dir><dir><a name='):
            break
        else:
            raise ValueError('ERROR: Unknown line format:\n{}\non {}'
                                 .format(line, url))
    links = list('\t'.join([x, '\t'.join(y)]) for x, y in links.items())

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
    print()
exit()
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

re0 = re.compile(r'<p>((?:.|\n)*?)</p>')
re1 = re.compile(r'<.*?>')
need_enter = False
for link_no, link in enumerate(links, start=1):
    link, header = link.split('\t')
    #header = unescape(header).replace('\u200b', '') \
    #                         .replace('\ufeff', '').strip()
    header = utils.norm_text2(header)
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    #link = 'https://www.interfax.ru/interview/374150'
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
    lines = []
    for line in res:
        #line = unescape(re1.sub('', line)).replace('\u200b', '') \
        #                                  .replace('\ufeff', '') \
        #                                  .replace('й', 'й') \
        #                                  .replace('ё', 'ё') \
        #                                  .strip()
        line = utils.norm_text2(re1.sub('', line))
        if line:
            lines.append(' '.join(line.split()))
    if len(lines) >= _utils.MIN_TEXT_LINES:
        texts_total += 1
        if link_no > start_link_idx:
            with open(page_fn, 'wt', encoding='utf-8') as f:
                print(link, file=f)
                f.write(page)
        with open(text_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            print(header, file=f)
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
_utils.make_chunks(num_links)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(num_links, isdialog=False)
